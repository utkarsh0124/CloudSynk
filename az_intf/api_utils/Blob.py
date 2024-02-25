import shared_variable
from azure.storage.blob import BlobBlock

import uuid
import os

class Blob:
    def __init__(self, container_client, container_name):
        self.__container_client = container_client
        self.__container_name = container_name

        #get blob list from local DB
        #made public for testing purpose. make it private
        self.blob_list = set()
    

    def __add_to_db(self, blob_name):
        #add new blob(blob_name) for __container_name to blob db

        #update blob_list
        self.blob_list.add(blob_name)
        pass


    def __delete_from_db(self, blob_name):
        #delete blob(blob_name) for __container_name to blob db

        #update blob_list
        self.blob_list.remove(blob_name)
        pass


    def get_list(self):
        return list(self.blob_list)
    
    
    def blob_exists(self, blob_name):
        return blob_name in self.blob_list
    
    
    def blob_create(self, file_path):
        operation_status = 0
        
        blob_name = file_path.split('/')[-1]
        print("Blob Name : ", blob_name)
        if self.blob_exists(blob_name):
            print("Blob Already Exists")
        else:
            try:
                ''' 
                Azure API call to create blob
                '''
                # Instantiate a new BlobClient
                blob_client = self.__container_client.get_blob_client(blob_name)
                
                #chunk size -> 4mb
                chunk_size=4*1024*1024
                block_list=[]
                with open(file_path, 'rb') as blob_file:
                    while True:
                        read_data = blob_file.read(chunk_size)
                        if not read_data:
                            break # done
                        blk_id = str(uuid.uuid4())
                        blob_client.stage_block(block_id=blk_id,data=read_data) 
                        block_list.append(BlobBlock(block_id=blk_id))
                        
                # Upload the whole chunk to azure storage and make up one blob
                blob_client.commit_block_list(block_list)

                #update db
                self.__add_to_db(blob_name)
                operation_status = 1

                shared_variable.increment_api_call_counter2()
            except Exception as error:
                print("BLOG CREATE EXCEPTION : ", error)
        return operation_status
    
        
    def blob_delete(self, blob_name):
        operation_status = 0
        
        # FOR TESTING PURPOSE ONLY
        # REMOVE THIS
        self.blob_list.add(blob_name)
        
        if self.blob_exists(blob_name):
            try:
                ''' 
                Azure API call to delete blob
                ''' 
                # Instantiate a new BlobClient
                blob_client = self.__container_client.get_blob_client(blob_name)
                
                # Delete content to blob
                blob_client.delete_blob()
                
                #update blob DB
                self.__delete_from_db(blob_name)
                operation_status = 1
            
                shared_variable.increment_api_call_counter2()
            except Exception as error:
                print("BLOB DELETE EXCEPTION : ", error)
        else :
            print("BLOB not found")
        return operation_status
    
    
    def download_blob(self, path_to_save, blob_name):
        operation_status = 0
        file_byte_arr = None
        blob_file = os.path.join(path_to_save, blob_name)
        
        if self.blob_exists(blob_name):
            try:
                '''
                AZURE API call to download blob
                '''
                # Instantiate a new BlobClient
                blob_client = self.__container_client.get_blob_client(blob_name)
                
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
        
        return operation_status
    
    
    def delete_all(self):
        ''' 
        AZURE API call to delete all blobs
        '''
        pass