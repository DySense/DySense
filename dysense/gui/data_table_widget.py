# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from PyQt4.Qt import *
from PyQt4 import QtGui

from dysense.core.utility import make_unicode, pretty, limit_decimal_places, format_decimal_places

class DataTableWidget(QWidget):
    
    def __init__(self, *args):
        QWidget.__init__(self, *args)

        self.setup_ui()
        
        # Associate sensor ID with list of metadata for each piece of data it outputs.
        self.sensor_id_to_data_info = {}
        
        # Associate row index with sensor ID
        self.row_index_to_sensor_id = {}
        self.sensor_id_to_row_index = {}
        
        # Track which sensors IDs have shown data in table.
        # key - sensor_id 
        # value - true if have already shown data in table for this sensor.
        self.sensor_id_to_data_status = {}
        
    def setup_ui(self):
        
        self.button_font = QtGui.QFont()
        self.button_font.setPointSize(12)
        
        table_font = QtGui.QFont()
        table_font.setPointSize(11)
        
        self.central_layout = QVBoxLayout(self)
        
        self.data_table = QTableWidget()
        self.data_table.setFont(table_font)
        self.data_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.data_table.verticalHeader().setVisible(False)
        self.data_table.cellClicked.connect(self.cell_clicked)
        self.data_table.cellDoubleClicked.connect(self.cell_double_clicked)
        
        self.hint_label = QLabel('Hint: Click a row to auto-update column sizes and header names')
        self.hint_label.setFont(QFont('label_font', pointSize=14))
        self.hint_label.setAlignment(Qt.AlignCenter)
        
        self.central_layout.addWidget(self.data_table)
        self.central_layout.addWidget(self.hint_label)
        
    def refresh_table(self):
        
        if len(self.sensor_id_to_data_info) == 0:
            self.data_table.setColumnCount(0)
            self.data_table.setRowCount(0)
            return # no sensors to show in table
        
        # First alphabetize sensors
        sorted_sensor_ids = sorted(self.sensor_id_to_data_info.keys())
        
        # Add one to for Sensor Name column
        required_columns = max([len(info) for info in self.sensor_id_to_data_info.values()])
        required_columns += 1

        # Remove all rows so we can re-add everything.
        self.data_table.setRowCount(0)
        self.row_index_to_sensor_id = {}
        self.sensor_id_to_row_index = {}
        
        self.data_table.setColumnCount(required_columns)
  
        for row_idx, sensor_id in enumerate(sorted_sensor_ids):

            info = self.sensor_id_to_data_info[sensor_id]
            
            self.data_table.insertRow(row_idx)
            
            self.row_index_to_sensor_id[row_idx] = sensor_id
            self.sensor_id_to_row_index[sensor_id] = row_idx
            
            for column_idx in range(required_columns):
            #for column_idx in range(len(info)):
                
                table_item = QTableWidgetItem()
                table_item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                
                # Works but greys everything out and prevents cells from being selected at all.
                #item_flags = Qt.ItemFlags()
                #item_flags = item_flags & (~Qt.ItemIsEditable)
                #table_item.setFlags(item_flags)
                
                if column_idx == 0:
                    table_item.setText(sensor_id)
                    
                if column_idx > len(info):
                    # Gray out cells that shouldn't have data.
                    table_item.setBackground(QtGui.QColor(150,150,150))
                    
                self.data_table.setItem(row_idx, column_idx, table_item)
                
            # Default to showing column headers for first sensor
            if row_idx == 0:
                column_headers = self.get_all_column_headers(info)
                self.data_table.setHorizontalHeaderLabels(column_headers)  

        self.data_table.resizeColumnsToContents()
        # If set to stretch then user can't resize columns.
        #self.data_table.horizontalHeader().setResizeMode(QtGui.QHeaderView.Stretch)
        #self.data_table.horizontalHeader().setStretchLastSection(True)
        
    def add_sensor(self, sensor_id, sensor_info):
        
        data_info = sensor_info['metadata']['data']
        
        self.sensor_id_to_data_info[sensor_id] = data_info
        
        # Indicate that haven't shown data for this sensor yet.
        self.sensor_id_to_data_status[sensor_id] = False
        
        self.refresh_table()
    
    def remove_sensor(self, sensor_id):
        
        del self.sensor_id_to_data_info[sensor_id]
        
        self.refresh_table()

    def cell_clicked(self, row_idx, col_idx):
        
        # Use row index that was clicked on to find corresponding sensor info.
        sensor_id = self.row_index_to_sensor_id[row_idx]
        data_info = self.sensor_id_to_data_info[sensor_id]
        
        column_headers = self.get_all_column_headers(data_info)
        
        self.data_table.setHorizontalHeaderLabels(column_headers)
        
        self.data_table.resizeColumnsToContents()
        
    def cell_double_clicked(self, row_idx, col_idx):
        # Treat this as a single click since user shouldn't be able to edit the cell contents.
        self.cell_clicked(row_idx, col_idx)
        
    def get_all_column_headers(self, data_info):
        
        column_headers = self.get_data_column_headers(data_info)
        
        column_headers.insert(0, 'Sensor Name')
        
        num_blank_columns = self.data_table.columnCount() - len(column_headers)
        if num_blank_columns > 0:
            column_headers += [''] * num_blank_columns
            
        return column_headers
        
    def get_data_column_headers(self, data_info):
        
        data_column_headers = []
        for data_element in data_info:
            
            column_name = pretty(data_element['name'])
            
            try:
                column_name +=  '\n({})'.format(data_element['units'])
            except KeyError:
                pass # don't include units

            data_column_headers.append(column_name)
            
        return data_column_headers
    
    def refresh_sensor_data(self, sensor_id, new_set_of_data):
        
        row_index = self.sensor_id_to_row_index[sensor_id]
        data_info = self.sensor_id_to_data_info[sensor_id]
        
        for i, data_value in enumerate(new_set_of_data):
            
            # Add one since first column is sensor name.
            column_index = i + 1
            
            table_item = self.data_table.item(row_index, column_index)
            if table_item is None:
                continue # set of data is larger than expected
            
            if isinstance(data_value, float):
                try:
                    desired_decimal_places = data_info[i]['decimal_places']
                    data_value = format_decimal_places(data_value, desired_decimal_places)
                except KeyError:
                    # Number of decimals not specified so limit at 5.
                    data_value = limit_decimal_places(data_value, 5)

            table_item.setText(make_unicode(data_value))
            
        if not self.sensor_id_to_data_status[sensor_id]:
            # First time showing data for this sensor show make sure columns are big enough to show it.
            self.data_table.resizeColumnsToContents()
        else:
            # Remember that we've shown data for this sensor because constantly resizing looks funny.
            self.sensor_id_to_data_status[sensor_id] = True
