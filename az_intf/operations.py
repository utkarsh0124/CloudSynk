from .models import Blob
from django.utils import timezone

def assign_container(username:str):
    #get new container assigned to the user from azure
    container_name = username + "_container"
    return container_name

def add_file(file_name:str, container_name:str):
    ret = 0
    blob_exists = Blob.objects.filter(blob_name=file_name).count()
    if blob_exists == 0:
        #add blob using azure API
        
        #add record in Blob DB
        Blob.objects.create(
            blob_name=file_name, 
            blob_size=0, 
            container_name=container_name, 
            blob_update_time=timezone.now()
            )
        ret = 1
    else:
        print("Blob ALREADY EXISTS")
    return ret

    
def delete_file(file_name:str):
    ret = 0
    blob_exists = Blob.objects.filter(blob_name=file_name).count()
    if blob_exists == 0:
        print("Blob DOES NOT EXISTS")
    else:
        #Delete blob using Azure API
        
        #update record in Blob DB   
        blob = Blob.objects.get(blob_name=file_name)
        blob.delete()
        ret = 1
    return ret

def get_blob_size(file_name:str):
    blob_exists = Blob.objects.filter(blob_name=file_name).count()
    if blob_exists == 0:
        print("Blob DOES NOT EXISTS")
    else:
        #Delete blob using Azure API
        blob = Blob.objects.get(blob_name=file_name)
        return blob.blob_size
    return 0
    
    
def list_files(container_name:str):
    blob_list = Blob.objects.filter(container_name=container_name)

    if blob_list.count() != 0:
        return blob_list
    return []