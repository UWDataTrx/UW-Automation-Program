import sys
sys.path.append('.')
from utils.utils import write_shared_log
from unittest.mock import patch
import getpass

# Test unknown user handling
with patch.object(getpass, 'getuser', return_value='TestUser123'):
    write_shared_log('test_unknown_user', 'Testing unknown user handling', 'TEST')
