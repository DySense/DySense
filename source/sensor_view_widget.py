
from PyQt4.QtGui import *
from sensor_view_widget_designer import Ui_Form
from PyQt4 import QtGui

class SensorViewWidget(QWidget,Ui_Form):
           
    def __init__(self, controller_id, sensor_info, presenter):
        #super().__init__()
        QWidget.__init__(self)
        self.setupUi(self) #call the auto-generated setupUi function in the designer file
        
        self.presenter = presenter
        self.controller_id = controller_id
        self.sensor_info = sensor_info              
                
        self.name_to_object =  {
                               'sensor_type': self.sensor_type_line_edit,
                               'sensor_name': self.sensor_name_line_edit,                                      
                               'sensor_state': self.sensor_state_line_edit,
                               #<info name of serial number>: self.sensor_id_line_edit #need to associate with the serial number
                                
                                                    
                               }
        
        self.object_to_name =  {
                               #self.sensor_id_line_edit: '<info name of serial number>', #may need to be added. 
                               self.sensor_type_line_edit: 'sensor_type',
                               self.sensor_name_line_edit: 'sensor_name',                                      
                               self.sensor_state_line_edit: 'sensor_state',                                                     
                               }
             
        
        self.settings_name_to_object = {
                                        'output_rate': self.capture_rate_line_edit                                                                           
                                        }
        
        #setup health icons #TODO crop whitespace from edges of icons and figure out why good_icon pixmap is null
        self.neutral_icon = QtGui.QPixmap('../resources/grey_neutral_icon.png')
        self.neutral_icon = self.neutral_icon.scaled(65,63)      
        self.good_icon = QtGui.QPixmap('../resources/green_check_icon.png')
        self.good_icon = self.good_icon.scaled(65,63)
        self.bad_icon = QtGui.QPixmap('../resources/red_x_icon.png')
        self.bad_icon = self.bad_icon.scaled(65,63)
        
        
        #Set fields not to be edited by user as read only
        self.sensor_message_center_text_edit.setReadOnly(True)
        self.sensor_state_line_edit.setReadOnly(True)    
        
        #Connect User Changes        
        #self.sensor_name_line_edit.textEdited.connect(self.sensor_name_changed)
        self.sensor_name_line_edit.editingFinished.connect(self.sensor_name_changed)
                      
        #Connect main command buttons
        self.connect_sensor_button.clicked.connect(self.connect_sensor_button_clicked)
        self.pause_sensor_button.clicked.connect(self.pause_sensor_button_clicked)
        self.remove_sensor_button.clicked.connect(self.remove_sensor_button_clicked)
        
        #Connect extra command buttons
        self.extra_command1_button.clicked.connect(self.extra_command1_button_clicked)
        self.extra_command2_button.clicked.connect(self.extra_command2_button_clicked)
        self.clear_sensor_message_center_button.clicked.connect(self.clear_sensor_message_center_button_clicked)
    
    
    #Update Viewer
    def update_sensor_view(self, info_name, value):       
          
        if self.name_to_object.has_key(info_name):
            obj = self.name_to_object[info_name]
            obj.setText(value)
        
        #get values from settings dict    
        if info_name == 'settings':
            settings = value
            for key in settings:
                if self.settings_name_to_object.has_key(key):
                    obj = self.settings_name_to_object[key]
                    obj.setText(str(settings[key]))
                   
        if info_name == 'sensor_health':
            self.sensor_health_update(value)                        
            
    
    
    
    def sensor_name_changed(self):    
        
        new_name = str(self.sensor_name_line_edit.text())
        self.presenter.change_sensor_info('sensor_name', new_name)
         
         
         
    #TODO add in the 'neutral' health state if there is one
    def sensor_health_update(self, health):
        if health == 'N/A':
            self.sensor_health_icon_label.setPixmap(self.neutral_icon)    
    
        elif health == 'good':
            self.sensor_health_icon_label.setPixmap(self.good_icon)
            
        elif health == 'bad':
            self.sensor_health_icon_label.setPixmap(self.bad_icon)
    
        
    def clear_sensor_message_center_button_clicked(self):
        self.sensor_message_center_text_edit.clear() 
    
    
    #Main Commands
    def connect_sensor_button_clicked(self):
        print 'connect sensor button clicked'
        
    def pause_sensor_button_clicked(self):
        print 'pause sensor button clicked'
        
    def remove_sensor_button_clicked(self):    
        self.presenter.remove_sensor(self.sensor_id)    
        print 'remove sensor button clicked'
        
        
    def extra_command1_button_clicked(self):
        self.sensor_message_center_text_edit.setText(str(self.sensor_info['metadata']))
        
        print 'extra command 1 clicked'
        
    def extra_command2_button_clicked(self):
        print'extra command 2 clicked'
            