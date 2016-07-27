#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys

from PyQt4.Qt import *
from PyQt4 import QtGui

from dysense.core.utility import get_from_list

class IssuesDialog(QDialog):
    
    def __init__(self, *args):
        QDialog.__init__(self, *args)
        
    def setup_ui(self):
        
        pass
    
    def ack_all_issues_button_clicked(self):
        self.presenter.acknowledge_issue({}, ack_all_issues=True)
    
    def refresh_current_issues(self, current_issues):
        
        # Remove all rows so we can re-add everything.
        self.current_issues_table.setRowCount(0)
        
        if len(current_issues) == 0:
            self.current_issues_table.setColumnCount(0)
            return # no issues to show in table
        
        self.issue_table_headers = ['Controller ID', 'Sub ID', 'Issue Type', 'Level', 'Reason', 'Acknowledged', 'Resolved', 'Duration']
        self.current_issues_table.setColumnCount(len(self.issue_table_headers))
        self.current_issues_table.setHorizontalHeaderLabels(self.issue_table_headers)
  
        for row_idx, issue in enumerate(current_issues):
            acked = 'Yes' if issue.acked else 'No'
            resolved = 'Yes' if issue.resolved else 'No'
            duration = issue.expiration_time - issue.start_time
            if duration < 0:
                duration = '' # issue doesn't have an end time yet.
            else:
                duration = '{:.2f}'.format(duration)
                
            table_values = [issue.id, issue.sub_id, pretty(issue.issue_type), pretty(issue.level),
                             issue.reason, acked, resolved, duration]
            
            self.current_issues_table.insertRow(row_idx)
            
            for column_idx, table_value in enumerate(table_values):
                
                table_item = QTableWidgetItem(table_value)
                table_item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                
                self.current_issues_table.setItem(row_idx, column_idx, table_item)
                
                if issue.resolved:
                    table_item.setBackground(QtGui.QColor(194,248,255))
                
        self.current_issues_table.resizeColumnsToContents()
        #self.current_issues_table.horizontalHeader().setResizeMode(QtGui.QHeaderView.Stretch)
        self.current_issues_table.horizontalHeader().setStretchLastSection(True)
                
    def current_issue_clicked_on(self, row_idx, column_idx):
        
        self.presenter.acknowledge_issue_by_index(row_idx)