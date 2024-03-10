# import sys
# sys.path.append("...")

# import shared_variable
from azure.storage.blob import BlobBlock
from main.models import Blob as blob_table

import uuid
import os
from datetime import datetime

class Blob:
    def __init__(self, container_client, container_name:str):
        self.__container_client = container_client
        self.__container_name = container_name
        # dict<str, set()>
        self.__container_blob_dict = {
                    self.__container_name : set([_.blob_name for _ in blob_table.objects.filter(container_name=self.__container_name)])
                }

        
        print("blob list :  ", end="  ")
        if self.__container_name in self.__container_blob_dict.keys():
            for _ in self.__container_blob_dict[self.__container_name]:
                print(_, end=' : ')
            print()


    def __add_to_dict(self, blob_name:str):
        if not self.blob_exists(blob_name):
            self.__container_blob_dict[self.__container_name].add(blob_name)
        else:
            print("ERROR :: Blob.py :: __add_to_dict() :: Blob Already present Cannot Add to dict")


    def __remove_from_dict(self, blob_name:str):
        if self.blob_exists(blob_name):
            self.__container_blob_dict[self.__container_name].remove(blob_name)
        else:
            print("ERROR :: Blob.py :: __remove_from_dict() :: Blob not present Cannot Delete from Dict")


    def __add_to_db(self, blob_name:str):
        new_blob_entry = blob_table()
        
        new_blob_entry.blob_name = blob_name
        new_blob_entry.container_name = self.__container_name
        new_blob_entry.blob_size = 0
        new_blob_entry.blob_update_time = datetime.now()
        new_blob_entry.save()

        # udpate dict
        self.__add_to_dict(blob_name)


    def __delete_from_db(self, blob_name:str):
        blob_obj = blob_table.objects.get(blob_name=blob_name, container_name=self.__container_name)        
        blob_obj.delete()

        #update dict
        self.__remove_from_dict(blob_name)


    def get_list(self):
        if self.__container_name in self.__container_blob_dict:
            return list(self.__container_blob_dict[self.__container_name])
        else:
            print("\n   [INFO :: Blob.py :: get_list() :: Container not present in Dict]\n")
            return []
    

    def blob_exists(self, blob_name:str):
        if self.__container_name in self.__container_blob_dict.keys():
            return blob_name in self.__container_blob_dict[self.__container_name]
        else:
            return False

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
                # # Instantiate a new BlobClient
                # blob_client = self.__container_client.get_blob_client(blob_name)
                
                # #chunk size -> 4mb
                # chunk_size=4*1024*1024
                # block_list=[]
                # with open(file_path, 'rb') as blob_file:
                #     while True:
                #         read_data = blob_file.read(chunk_size)
                #         if not read_data:
                #             break # done
                #         blk_id = str(uuid.uuid4())
                #         blob_client.stage_block(block_id=blk_id,data=read_data) 
                #         block_list.append(BlobBlock(block_id=blk_id))
                        
                # # Upload the whole chunk to azure storage and make up one blob
                # blob_client.commit_block_list(block_list)

                #update db
                self.__add_to_db(blob_name)
                operation_status = 1

                #shared_variable.increment_api_call_counter2()
            except Exception as error:
                print("BLOG CREATE EXCEPTION : ", error)
        return operation_status
    
        
    def blob_delete(self, blob_name):
        operation_status = 0
        
        # FOR TESTING PURPOSE ONLY
        # REMOVE THIS
        
        if self.blob_exists(blob_name):
            try:
                ''' 
                # Azure API call to delete blob
                # ''' 
                # # Instantiate a new BlobClient
                # blob_client = self.__container_client.get_blob_client(blob_name)
                
                # # Delete content to blob
                # blob_client.delete_blob()
                
                #update blob DB
                self.__delete_from_db(blob_name)
                operation_status = 1
                
                #shared_variable.increment_api_call_counter2()
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
                # # Instantiate a new BlobClient
                # blob_client = self.__container_client.get_blob_client(blob_name)
                
                # # Read data in chunks to avoid loading all into memory at once
                # with open(blob_file, "wb") as my_blob:
                #     download_stream = blob_client.download_blob()
                #     my_blob.write(download_stream.readall())
                
                # operation_status = 1

                #shared_variable.increment_api_call_counter2()
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