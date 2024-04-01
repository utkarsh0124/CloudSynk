''' 
GLOBAL VARIABLES
'''
AZURE_API_CALL_COUNT = 0

def increment_api_call_counter():
    #update API_CALL_COUNT
    global AZURE_API_CALL_COUNT
    AZURE_API_CALL_COUNT += 1
    
def increment_api_call_counter2():
    #update API_CALL_COUNT
    global AZURE_API_CALL_COUNT
    AZURE_API_CALL_COUNT += 1
    AZURE_API_CALL_COUNT += 1