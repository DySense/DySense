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
        // Unique sensor ID.
        string sensorID;

        // Controller endpoint to connect to and get message from.
        string connectEndpoint;

        // Minimum duration (in seconds) that data collection loop will run.
        public double MinLoopPeriod { get; set; }

        // Maximum number of seconds sensor needs to wrap up before being force closed.
        public double MaxClosingTime { get; set; }

        // How often (in seconds) we should receive a new message from client and how often we should send one back.
        double heartbeatPeriod = 0.1;

        // If set to true then sensor won't start collecting data until it has a valid UTC time.
        bool waitForValidTime = true;

        // Set to true when receive 'close' command from client.
        bool receivedCloseRequest = false;

        // Status fields - private to ensure client is notified when one changes.
        bool _paused = true;
        string _health = "bad";

        // Time references used to improve precision when sensor requests current time.
        double lastReceivedSysTime = 0;
        double lastReceivedUTCTime = 0;

        // ZMQ socket for talking to sensor controller.
        ZContext context;
        ZSocket socket;

        // If we don't receive a new message in this time then consider client dead. (in seconds) 
        double clientTimeoutThresh;
        
        // How long to wait for client to send first message before timing out. (in seconds)
        double maxTimeToReceiveMessage;
        
        // Last system time that we tried to process new messages from client.
        double lastMessageProcessingTime;
        
        // Last system time that we received a new message from client.
        double lastReceivedMessageTime;
        
        // Last time sensor sent out heartbeat message.
        double lastSentHeartbeatTime;
        
        // Time that interface was connected to client.
        double interfaceConnectionTime;
    
        // How many message have been received from client.
        int numMessageReceived;

        // Associate callback methods with different message types.
        Dictionary<string, Func<object, bool>> messageTable;

        public SensorBase(string sensorID, string connectEndpoint, double minLoopPeriod = 0,
            double maxClosingTime=0, double heartbeatPeriod=0.5, bool waitForValidTime=true)
        {
            this.sensorID = sensorID;
            this.connectEndpoint = connectEndpoint;
            this.MinLoopPeriod = minLoopPeriod;
            this.MaxClosingTime = maxClosingTime;
            this.heartbeatPeriod = Math.Max(0.1, heartbeatPeriod);
            this.waitForValidTime = waitForValidTime;
            this.clientTimeoutThresh = this.heartbeatPeriod * 10;
            this.maxTimeToReceiveMessage = this.clientTimeoutThresh * 1.5;
            
            messageTable = new Dictionary<string,Func<object, bool>> 
            { 
                { "command", HandleCommand }, 
                { "time", HandleNewTime },
                { "heartbeat", HandleNewHeartbeat },
            };
        }

        public double Time
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

        public double SysTime { get { return (DateTime.Now.ToUniversalTime() - new DateTime (1970, 1, 1)).TotalSeconds; } }
    
        public bool Paused 
        {
            get  { return this._paused; }
            set 
            {
                this._paused = value;
                SendStatusUpdate();
            }
        }

        public string Health 
        {
            get  { return this._health; }
            set 
            {
                bool needToSendUpdate = (value != this._health);
                this._health = value;
                if (needToSendUpdate)
                {
                    SendStatusUpdate();
                }
            }
        }

        // Set everything up, collect data and then close everything down when finished.
        public void Run()
        {
            try 
	        {	        
		        SetupInterface();
                Setup();

                while (true)
                {
                    // Save off time so we can limit how fast loop runs.
                    double loopStartTime = SysTime;

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

                    if (waitForValidTime && (Time == 0))
                    {
                        // Don't read data from sensor until we have a valid timestamp for it.
                        continue;
                    }

                    if (Paused)
                    {
                        //await Task.Delay(100);
                        Thread.Sleep(100);
                        continue;
                    }

                    // Give the sensor a chance to read in new data.
                    ReadNewData();

                    double loopDuration = SysTime - loopStartTime;
                    if (loopDuration < this.MinLoopPeriod)
                    {
                        double timeToWait = this.MinLoopPeriod - loopDuration;
                        Thread.Sleep((int)(Math.Max(0, timeToWait) * 1000));
                        //await Task.Delay((int)(Math.Max(0, timeToWait)*1000));
                    }
                }
	        }
	        catch (Exception e)
	        {
		        SendText(e.ToString());
	        }
            finally
            {
                this.receivedCloseRequest = false;
                Pause();
                Close();
                CloseInterface();
            }
        }

        // Stop reading sensor data and close down any resources.
        protected abstract void Close();

        // Return true if sensor is closed.
        protected abstract bool IsClosed();

        // Try to read in new data from sensor.  Only called when not paused.
        protected abstract void ReadNewData();

        // Called before collection loop starts. Driver can override to make connection to sensor.
        protected virtual void Setup() { return; }

        // Called when pause command is received or sensor closes. Driver can override to notify sensor.
        protected virtual void Pause() { return; }

        // Called when resume command is received. Driver can override to notify sensor.
        protected virtual void Resume() { return; }

        // Override to handle sensor specified commands (e.g. trigger)
        protected virtual void HandleSpecialCommand(string command) { return; }

        // Set up client socket and then send status update to controller.
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

        // Notify client of status change (status = health + state)
        private void SendStatusUpdate()
        {
            string state = (this.Paused ? "paused" : " started");
            SendMessage("new_sensor_status", new List<string>() { state, this.Health });
        }

        // Send unlabeled data to client
        protected void HandleData(List<object> data)
        {
            SendMessage("new_sensor_data", new List<List<object>>() { data });
        }

        // Send labeled data to client.
        protected void HandleData(Dictionary<string, object> data)
        {
            SendMessage("new_sensor_data", data);
        }

        // Send text message to client (like print)
        protected void SendText(string text)
        {
            SendMessage("new_sensor_text", text);
        }

        // Send message to client in JSON format.
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

        // Deal with a new command (e.g. 'close') received from client.
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


        // Process new time reference received from client.
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

        // Return true if it's been too long since we've received a new message from client.
        private bool ClientTimedOut()
        {
            if ((interfaceConnectionTime == 0) || (lastMessageProcessingTime == 0))
            {
                // Haven't tried to receive any messages yet so can't know if we're timed out.
                return false;
            }

            if (numMessageReceived == 0)
            {
                // Give client more time to send first message.
                double timeSinceConnecting = lastMessageProcessingTime - interfaceConnectionTime;
                return timeSinceConnecting > maxTimeToReceiveMessage;
            }

            double timeSinceLastMessage = lastMessageProcessingTime - lastReceivedMessageTime;
            return timeSinceLastMessage > clientTimeoutThresh;
        }

        // Return true if it's time to send a heartbeat message to client.
        private bool NeedToSendHeartbeat()
        {
            double timeSinceLastHearbeat = SysTime - lastSentHeartbeatTime;
            return timeSinceLastHearbeat > heartbeatPeriod;
        }
    }
}
