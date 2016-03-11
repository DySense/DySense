using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Threading;
using Newtonsoft.Json;
using ZeroMQ;

namespace DySense
{
    /// <summary>
    /// Base class for all sensor drivers.
    /// All sensor drivers written in C# should inherit from this class. Most of its public interface
    /// is over sockets where inputs are time/commands and outputs are data/messages/status. The only
    /// public method is run() which handles everything.
    /// </summary>
    abstract public class SensorBase
    {
        // The keys are the possible states the driver can be in.
        // The values are the 'health' associated with each state.
        static Dictionary<string, string> possibleStates = new Dictionary<string, string>
        {
            { "closed", "neutral" },
            { "waiting_for_time", "neutral" },
            { "normal", "good" },
            { "timed_out", "bad" },
            { "error", "bad" },
        };

        // Unique sensor ID.
        string sensorID;

        // Controller endpoint to connect to and get messages from.
        string connectEndpoint;

        // The expected duration (in seconds) between sequential sensor reads.
        protected double DesiredReadPeriod { get; set; }

        // Maximum number of seconds sensor needs to wrap up before being force closed.
        protected double MaxClosingTime { get; set; }

        // How often (in seconds) we should receive a new message from controller and how often we should send one back.
        double heartbeatPeriod = 0.1;

        // If set to true then sensor won't start collecting data until it has a valid UTC time.
        bool waitForValidTime = true;

        // If set to true then if the sensor base will determine if a time out is caused by the sensor actually timing out
        // or just returning to run the process loop.  This can be set to false if the sensor has multiple sources that come
        // in at different times and need to be monitored separately.
        bool DecideTimeout { get; set; }

        // Set to true when receive 'close' command from controller.
        bool receivedCloseRequest = false;

        // Current sensor state. Private to keep in ensure controller is notified when changes.
        // The corresponding health can be requested from the health property.
        string _state = "closed";

        // How often the main processing in run() should be executed. At least run
        // at 5Hz to keep things responsive.
        double mainLoopProcessingPeriod;
        
        // How long the readNewData() method is allowed to run without returning.
        protected double MaxReadNewDataPeriod { get; private set; }
        
        // True if sensor shouldn't be saving/sending any data.
        bool _paused = true;

        // This is a flag that the readNewData() method can use to track whether or not it needs to
        // request new data, or it's still waiting on data to come in.  The idea is the function can't
        // block for too long so it needs a way to track the state of the read between calls.
        bool stillWaitingForData = false;

        // Time references used to improve precision when sensor requests current time.
        double lastReceivedSysTime = 0;
        double lastReceivedUTCTime = 0;

        // ZMQ socket for talking to sensor controller.
        ZContext context;
        ZSocket socket;

        // The time to run next run each loop.  Used to figure out how long to wait after each run.
        double nextProcessingLoopStartTime = 0;
        double nextSensorLoopStartTime = 0;

        // System time that data was last received from the sensor.
        double lastReceivedDataTime = 0;

        // If we don't receive a new message in this time then consider controller dead. (in seconds) 
        double clientTimeoutThresh;
        
        // How long to wait for controller to send first message before timing out. (in seconds)
        double maxTimeToReceiveMessage;
        
        // Last system time that we tried to process new messages from controller.
        double lastMessageProcessingTime;
        
        // Last system time that we received a new message from controller.
        double lastReceivedMessageTime;
        
        // Last time sensor sent out heartbeat message.
        double lastSentHeartbeatTime;
        
        // Time that interface was connected to controller.
        double interfaceConnectionTime;
    
        // How many message have been received from controller.
        int numMessageReceived = 0;

        // How many message 'data' messages have been sent to controller.
        protected int NumDataMessageSent { get; private set; }

        // Associate callback methods with different message types.
        Dictionary<string, Func<object, bool>> messageTable;

        public SensorBase(string sensorID, string connectEndpoint, double desiredReadPeriod = 0.25, double maxClosingTime=0,
                          double heartbeatPeriod=0.5, bool waitForValidTime=true, bool decideTimeout=true)
        {
            this.sensorID = sensorID;
            this.connectEndpoint = connectEndpoint;
            this.DesiredReadPeriod = desiredReadPeriod;
            this.MaxClosingTime = maxClosingTime;
            this.heartbeatPeriod = Math.Max(0.1, heartbeatPeriod);
            this.mainLoopProcessingPeriod = Math.Min(this.heartbeatPeriod, 0.2);
            this.MaxReadNewDataPeriod = this.mainLoopProcessingPeriod * .9;
            this.waitForValidTime = waitForValidTime;
            this.DecideTimeout = decideTimeout;
            this.clientTimeoutThresh = this.heartbeatPeriod * 10;
            this.maxTimeToReceiveMessage = this.clientTimeoutThresh * 1.5;
            this.NumDataMessageSent = 0;

            messageTable = new Dictionary<string,Func<object, bool>> 
            { 
                { "command", HandleCommand }, 
                { "time", HandleNewTime },
                { "heartbeat", HandleNewHeartbeat },
            };
        }

        // Return current UTC time (from sensor controller).  Uses system time offset since last received message to improve resolution.
        public double UtcTime
        {
            get 
            {
                double utcTime = this.lastReceivedUTCTime;
                if (utcTime > 0)
                {
                    // Account for time that has elapsed since last time we received a message.
                    double elapsedTime = SysTime - this.lastReceivedSysTime;
                    if (elapsedTime > 0)
                    {
                        utcTime += elapsedTime;
                    }
                }
                return utcTime;
            }
        }

        // Return current system time in seconds.
        public double SysTime { get { return (DateTime.Now.ToUniversalTime() - new DateTime (1970, 1, 1)).TotalSeconds; } }

        // Current driver state.
        public string State
        {
            get { return this._state; }
            set
            {
                if (value == this._state)
                {
                    return; // same state so don't keep sending updates.
                }
                if (!possibleStates.ContainsKey(value))
                {
                    throw new Exception(String.Format("Invalid sensor state {0}", value));
                }
                this._state = value;
                SendStatusUpdate();
            }
        }

        // Health corresponding to the current sensor state.
        public string Health
        {
            get { return possibleStates[State]; }
        }

        // True if sensor is in a paused state.
        public bool Paused 
        {
            get  { return this._paused; }
            set 
            {
                // Prevent from constantly sending status updates when nothings changing.
                if (value != this._paused)
                {
                    this._paused = value;
                    SendStatusUpdate(); 
                }
            }
        }

        // Set everything up, collect data and then close everything down when finished.
        public void Run()
        {
            try 
	        {
                // Setup ZMQ sockets and then give sensor driver a chance to set itself up.
		        SetupInterface();
                Setup();

                while (true)
                {
                    if (NeedToRunProcessingLoop())
                    {
                        // Save off time so we can limit how fast loop runs.
                        nextProcessingLoopStartTime = SysTime + mainLoopProcessingPeriod;

                        // Handle any messages received over socket.
                        ProcessNewMessages();

                        if (ClientTimedOut())
                        {
                            throw new Exception("Controller connection timed out.");
                        }

                        if (receivedCloseRequest)
                        {
                            SendText("Closing...");
                            break; // end main loop
                        }

                        if (NeedToSendHeartbeat())
                        {
                            SendMessage("new_sensor_heartbeat", " ");
                            this.lastSentHeartbeatTime = SysTime;
                        }
                    }

                    if (NeedToRunSensorLoop())
                    {
                        // Save off time so we can limit how fast the loop runs.
                        nextSensorLoopStartTime = SysTime + DesiredReadPeriod;

                        if (!stillWaitingForData)
                        {
                            RequestNewData();
                        }

                        string reportedState = ReadNewData();

                        if (reportedState == "timed_out")
                        {
                            if (ShouldHaveNewReading() || !DecideTimeout)
                            {
                                // Sensor actually did time out so we want to request new data.
                                stillWaitingForData = false;
                            }
                            else
                            {
                                // Didn't actually time out.. just returned to process new controller messages.
                                reportedState = "normal";
                                stillWaitingForData = true;
                            }
                        }

                        // If sensor is ok then override state if we're still waiting for a valid time.
                        bool reportedBadState = possibleStates[reportedState] == "bad";
                        bool waitingForTime = waitForValidTime && UtcTime == 0;
                        if (!reportedBadState && waitingForTime)
                        {
                            reportedState = "waiting_for_time";
                        }

                        this.State = reportedState;
                    }

                    // Figure out how long to wait before one of the loops needs to run again.
                    double nextTimeToRun = Math.Min(nextProcessingLoopStartTime, nextSensorLoopStartTime);
                    double timeToWait = nextTimeToRun - SysTime;
                    Thread.Sleep((int)(Math.Max(0, timeToWait) * 1000));
                }
	        }
	        catch (Exception e)
	        {
                State = "error";
		        SendText(e.ToString());
	        }
            finally
            {
                if (Health != "bad")
                {
                    // The closed state is only for when things closed down on request... not because an error occurred.
                    State = "closed";
                }
                this.receivedCloseRequest = false;
                SendEvent("closing");
                Pause();
                Close();
                CloseInterface();
            }
        }

        // Stop reading sensor data and close down any resources.
        protected abstract void Close();

        // Return true if sensor is closed.
        protected abstract bool IsClosed();

        // Request new data from sensor.
        protected virtual void RequestNewData() { return; }

        // Try to read in new data from sensor. Return new sensor state.
        protected abstract string ReadNewData();

        // Called before collection loop starts. Driver can override to make connection to sensor.
        protected virtual void Setup() { return; }

        // Called when pause command is received or sensor closes. Driver can override to notify sensor.
        protected virtual void Pause() { return; }

        // Called when resume command is received. Driver can override to notify sensor.
        protected virtual void Resume() { return; }

        // Override to handle sensor specified commands (e.g. trigger)
        protected virtual void HandleSpecialCommand(string command) { return; }

        // Return true if enough time has elapsed that the sensor should have returned a new reading.
        private bool ShouldHaveNewReading()
        {
            double timeSinceLastData = SysTime - lastReceivedDataTime;
            return timeSinceLastData >= DesiredReadPeriod;
        }

        // Set up controller socket and then send status update to controller.
        private void SetupInterface()
        {
            context = new ZContext();
            socket = new ZSocket(context, ZSocketType.DEALER);
            socket.Connect(this.connectEndpoint);

            SendStatusUpdate();
            interfaceConnectionTime = SysTime;
        }

        // Close down socket and ZMQ context.
        private void CloseInterface()
        {
            if (socket != null)
            {
                socket.Close();
            }
            if (context != null)
            {
                context.Terminate();
            }
        }

        // Notify controller of status change (status = state + health + paused)
        private void SendStatusUpdate()
        {
            SendMessage("new_sensor_status", new List<object>() { State, Health, Paused });
        }

        // Send data to controller
        protected void HandleData(List<object> data)
        {
            lastReceivedDataTime = SysTime;
            if (!ShouldRecordData())
            {
                return;
            }
            SendMessage("new_sensor_data", new List<List<object>>() { data });
            NumDataMessageSent += 1;
        }

        // Return true if the sensor is in a state where it should be trying to record data.
        protected bool ShouldRecordData()
        {
            bool stillNeedTimeReference = waitForValidTime && (UtcTime == 0);
            return !(stillNeedTimeReference || Paused);
        }

        // Send text message to controller (like print)
        protected void SendText(string text)
        {
            SendMessage("new_sensor_text", text);
        }

        // Send event to notify controller something important happened.
        protected void SendEvent(string eventName)
        {
            SendMessage("new_sensor_event", eventName);
        }

        // Send message to controller in JSON format.
        // Args:
        //    message_type - provide context of message being sent (e.g. 'text')
        //    message_body - list, dictionary or simple type.  All elements must be JSON serializable.
        private void SendMessage(string messageType, object messageBody)
        {
            var message = new Dictionary<string, object>
            {
                { "sensor_id", this.sensorID },
                { "type", messageType },
                { "body", messageBody },
            };
            string serializedMessage = JsonConvert.SerializeObject(message);
            socket.Send(new ZFrame(serializedMessage));
        }

        // Receive and process all messages in socket queue.
        private void ProcessNewMessages()
        {
            while (true)
            {
                ZError receiveError;
                var frame = socket.ReceiveFrame(ZSocketFlags.DontWait, out receiveError);
                if (frame == null) 
                {
                    break; // no more messages.
                }
                var message = JsonConvert.DeserializeObject<Dictionary<string,object>>(frame.ReadString());

                string messageType = (string)(message["type"]);
                var messageCallback = messageTable[messageType];
                messageCallback(message["body"]);

                this.numMessageReceived += 1;
                this.lastReceivedMessageTime = SysTime;
            }

            this.lastMessageProcessingTime = SysTime;
        }

        // Deal with a new command (e.g. 'close') received from controller.
        // If the command isn't a generic one then it will be passed to handleSpecialCommand.
        private bool HandleCommand(object body)
        {
            string command = (string)(body);

            switch (command)
            {
                case "close":
                    this.receivedCloseRequest = true;
                    break;
                case "pause":
                    this.Paused = true;
                    Pause();
                    break;
                case "resume":
                    this.Paused = false;
                    Resume();
                    break;
                default:
                    HandleSpecialCommand(command);
                    break;
            }

            return true;
        }

        // Process new time reference received from controller.
        // Correct for any time that has elapsed since utc time was last updated.
        // Save this time off so we can use it to calculate a more precise timestamp later. 
        // Args:
        //    times - list of (utc_time, sys_time) where sys_time is the system time from time.time()
        //            when utc_time was last updated.
        private bool HandleNewTime(object body)
        {
            double[] times = ((Newtonsoft.Json.Linq.JArray)body).ToObject<double[]>();
            double utcTime = times[0];
            double sysTime = times[1];
            this.lastReceivedSysTime = this.SysTime;
            double correctedUTCTime = utcTime + (this.lastReceivedSysTime - sysTime);
            this.lastReceivedUTCTime = correctedUTCTime;

            return true;
        }

        private bool HandleNewHeartbeat(object body)
        {
            // Don't need to do anything since all messages are treated as heartbeats.
            return true;
        }

        // Return true if it's been too long since we've received a new message from controller.
        private bool ClientTimedOut()
        {
            if ((interfaceConnectionTime == 0) || (lastMessageProcessingTime == 0))
            {
                // Haven't tried to receive any messages yet so can't know if we're timed out.
                return false;
            }

            if (numMessageReceived == 0)
            {
                // Give controller more time to send first message.
                double timeSinceConnecting = lastMessageProcessingTime - interfaceConnectionTime;
                return timeSinceConnecting > maxTimeToReceiveMessage;
            }

            double timeSinceLastMessage = lastMessageProcessingTime - lastReceivedMessageTime;
            return timeSinceLastMessage > clientTimeoutThresh;
        }

        // Return true if it's time to run interface processing loop.
        private bool NeedToRunProcessingLoop()
        {
            return SysTime >= nextProcessingLoopStartTime;
        }

        // Return true if it's time to run sensor processing loop.
        private bool NeedToRunSensorLoop()
        {
            return SysTime >= nextSensorLoopStartTime;
        }

        // Return true if it's time to send a heartbeat message to controller.
        private bool NeedToSendHeartbeat()
        {
            double timeSinceLastHearbeat = SysTime - lastSentHeartbeatTime;
            return timeSinceLastHearbeat > heartbeatPeriod;
        }
    }
}
