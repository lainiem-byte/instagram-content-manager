import traceback
import sys

try:
    from google import genai
    print('OK genai imported')
except Exception as e:
    traceback.print_exc(file=sys.stdout)
