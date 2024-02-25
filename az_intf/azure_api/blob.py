import shared_variable
from azure_api.container import Container
from azure.storage.blob import BlobBlock

import uuid
import os

class Blob:
    def __init__(self, container_client, container_name):
        self.container_client = container_client
        self.container_name = container_name
        
        self.blob_dict = dict()
        
        print("BLOB for container : ", self.container_name)
    
        
    def get_list(self):
        ''' 
        Azure API call to get list of blobs
        '''
        print("get_blob_dict")
        
        return self.blob_dict.keys()
    
    
    def blob_exists(self, blob_name):
        return blob_name in self.blob_dict
    
    
    def blob_create(self, file_path, blob_name):
        operation_status = 0
        
        if self.blob_exists(blob_name):
            print("Blob Already Exists")
        else:
            try:
                ''' 
                Azure API call to create blob
                '''
                # Instantiate a new BlobClient
                blob_client = self.container_client.get_blob_client(blob_name)
                
                #chunk size -> 4mb
                chunk_size=4*1024*1024
                block_list=[]
                with open(os.path.join(file_path, blob_name), 'rb') as blob_file:
                    while True:
                        read_data = blob_file.read(chunk_size)
                        if not read_data:
                            break # done
                        blk_id = str(uuid.uuid4())
                        blob_client.stage_block(block_id=blk_id,data=read_data) 
                        block_list.append(BlobBlock(block_id=blk_id))
                        
                # Upload the whole chunk to azure storage and make up one blob
                blob_client.commit_block_list(block_list)

                #update blob list
                self.blob_dict[blob_name] = 1
                operation_status = 1

                shared_variable.increment_api_call_counter2()
            except Exception as error:
                print("BLOG CREATE EXCEPTION : ", error)
        return operation_status
    
        
    def blob_delete(self, blob_name):
        operation_status = 0
        
        # FOR TESTING PURPOSE ONLY
        # REMOVE THIS
        self.blob_dict[blob_name]=1
        
        if self.blob_exists(blob_name):
            try:
                ''' 
                Azure API call to delete blob
                ''' 
                # Instantiate a new BlobClient
                blob_client = self.container_client.get_blob_client(blob_name)
                
                # Delete content to blob
                blob_client.delete_blob()
                
                #update blob list
                del self.blob_dict[blob_name]
                operation_status = 1
            
                shared_variable.increment_api_call_counter2()
            except Exception as error:
                print("BLOB DELETE EXCEPTION : ", error)
        else :
            print("BLOB not found")
        return operation_status
    
    
    def download_blob(self, path_to_save, blob_name):
        file_byte_arr = None
        blob_file = os.path.join(path_to_save, blob_name)
       
        #Remove this
        #Only for testing purpose
        self.blob_dict[blob_name] = 1
        
        if self.blob_exists(blob_name):
            try:
                '''
                AZURE API call to download blob
                '''
                # Instantiate a new BlobClient
                blob_client = self.container_client.get_blob_client(blob_name)
                
                # Read data in chunks to avoid loading all into memory at once
                with open(blob_file, "wb") as my_blob:
                    download_stream = blob_client.download_blob()
                    my_blob.write(download_stream.readall())
                
                operation_status = 1

                shared_variable.increment_api_call_counter2()
            except Exception as error:
                print("BLOB DOWNLOAD EXCEPTION, ", error)
        else :
            print("BLOB not found")
        return file_byte_arr
    
    
    def delete_all(self):
        ''' 
        AZURE API call to delete all blobs
        '''
        pass