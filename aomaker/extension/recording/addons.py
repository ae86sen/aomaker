import sys
import os
from aomaker.extension.recording.recording import Record

addons=[Record('iotiot.yaml', filter_str='iot.staging.com | ~hq Path\:\/alarm_record',
save_response=True, save_headers=False)]
