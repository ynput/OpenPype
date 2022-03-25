# -*- coding: utf-8 -*-
import os
import re

def match_aov_pattern(self, app, render_file_name):
    """Matching against a AOV pattern in the render files
    In order to match the AOV name
    we must compare against the render filename string 
    that we are grabbing the render filename string
    from the collection that we have grabbed from exp_files.    
    """
    
    if app in self.aov_filter.keys():
        for aov_pattern in self.aov_filter[app]:
            if re.match(aov_pattern, render_file_name):
                preview = True
                return preview