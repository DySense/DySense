# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from PyQt4.Qt import *
from PyQt4 import QtGui

from dysense.core.utility import make_unicode, pretty

class ControllerIssuesWidget(QWidget):
    
    def __init__(self, presenter, *args):
        QWidget.__init__(self, *args)

        self.presenter = presenter
        self.setup_ui()
        
    def setup_ui(self):
        
        self.button_font = QtGui.QFont()
        self.button_font.setPointSize(13)
        
        issue_table_font = QtGui.QFont()
        issue_table_font.setPointSize(11)
        
        self.central_layout = QVBoxLayout(self)
        
        self.current_issues_table = QTableWidget()
        self.current_issues_table.setFont(issue_table_font)
        self.current_issues_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        #self.current_issues_table.cellClicked.connect(self.current_issue_clicked_on)
        
        self.acknowledge_button = QPushButton("Acknowledge Issues")
        self.acknowledge_button.setFont(self.button_font)
        self.acknowledge_button.clicked.connect(self.acknowledge_button_clicked)
        self.acknowledge_button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        
        self.central_layout.addWidget(self.current_issues_table)
        self.central_layout.addWidget(self.acknowledge_button)
        
    def acknowledge_button_clicked(self):
        self.presenter.acknowledge_issue({}, ack_all_issues=True)
        
    def refresh_current_issues(self, current_issues):
        
        # Remove all rows so we can re-add everything.
        self.current_issues_table.setRowCount(0)
        
        if len(current_issues) == 0:
            self.current_issues_table.setColumnCount(0)
            return # no issues to show in table
        
        self.issue_table_headers = ['Item', 'Reason', 'Resolved', 'Duration', 'Level', 'Type']
        self.current_issues_table.setColumnCount(len(self.issue_table_headers))
        self.current_issues_table.setHorizontalHeaderLabels(self.issue_table_headers)
        
        # Make sure unresolved issues show up at top of list
        current_issues = sorted(current_issues, key=lambda issue: issue.resolved)
  
        for row_idx, issue in enumerate(current_issues):
            
            #if issue.resolved:
                # Include show active issues in this simple issue view.
                #continue
                
            resolved_value = 'Yes' if issue.resolved else 'No'
            
            issue_duration = issue.expiration_time - issue.start_time
            if issue_duration < 0:
                issue_duration = '' # issue doesn't have an end time yet.
            else:
                issue_duration = '{:.2f}'.format(issue_duration)
                
            table_values = [issue.sub_id, issue.reason, resolved_value, issue_duration, pretty(issue.level), pretty(issue.issue_type)]
            
            self.current_issues_table.insertRow(row_idx)
            
            for column_idx, table_value in enumerate(table_values):
                
                table_item = QTableWidgetItem(table_value)
                table_item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                
                self.current_issues_table.setItem(row_idx, column_idx, table_item)
                
                if issue.resolved:
                    table_item.setBackground(QtGui.QColor(194,248,255))
                
        self.current_issues_table.resizeColumnsToContents()
        #self.current_issues_table.horizontalHeader().setResizeMode(QtGui.QHeaderView.Stretch)
        #self.current_issues_table.horizontalHeader().setStretchLastSection(True)