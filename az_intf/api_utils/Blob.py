from azure.storage.blob import BlobType
from django.utils import timezone
from main.models import Blob as blob_table
from storage_webapp import logger, severity
from main.models import UserInfo

import uuid
import os


class Blob:
    def __init__(self, user_obj, container_client, container_name:str):
        self.__container_client = container_client
        self.__container_name = container_name
        self.__user_obj_info = UserInfo.objects.get(user=user_obj)

        # dict<str, set()>
        self.__container_blob_dict = {
                    self.__container_name : set([_.blob_name for _ in blob_table.objects.filter(user_id=self.__user_obj_info.user)])
                }
        
        logger.log(severity['INFO'], 'BLOB OBJECT CREATED : {}'.format(self.__container_name))


    def __add_to_dict(self, blob_name:str):
        if not self.blob_exists(blob_name):
            self.__container_blob_dict[self.__container_name].add(blob_name)
        else:
            logger.log(severity['ERROR'], 'BLOB ALREADY PRESENT CANNOT ADD TO DICT : {}'.format(blob_name))


    def __remove_from_dict(self, blob_name:str):
        if self.blob_exists(blob_name):
            self.__container_blob_dict[self.__container_name].remove(blob_name)
        else:
            logger.log(severity['ERROR'], 'BLOB NOT PRESENT CANNOT DELETE FROM DICT : {}'.format(blob_name))


    def __add_to_db(self, blob_name:str):
        new_blob_entry = blob_table()
        
        new_blob_entry.blob_name = blob_name
        new_blob_entry.container_name = self.__container_name
        new_blob_entry.blob_size = 0
        new_blob_entry.blob_update_time = timezone.now()
        new_blob_entry.save()

        # udpate dict
        self.__add_to_dict(blob_name)


    def __delete_from_db(self, blob_name:str):
        blob_obj = blob_table.objects.get(blob_name=blob_name, container_name=self.__container_name)        
        blob_obj.delete()

        #update dict
        self.__remove_from_dict(blob_name)
        logger.log(severity['INFO'], 'BLOB DELETED : {}'.format(blob_name))


    def get_list(self):
        if self.__container_name in self.__container_blob_dict:
            return list(self.__container_blob_dict[self.__container_name])
        else:
            logger.log(severity['ERROR'], 'CONTAINER NOT PRESENT IN DICT : {}'.format(self))
    

    def blob_exists(self, blob_name:str):
        if self.__container_name in self.__container_blob_dict.keys():
            logger.log(severity['INFO'], '{} Blob Exist'.format(blob_name))
            return blob_name in self.__container_blob_dict[self.__container_name]
        else:
            logger.log(severity['INFO'], 'BLOB DOES NOT EXIST : {}'.format(blob_name))
            return False


    def blob_create(self, uploaded_file, blob_name):
        operation_status = 0
        
        logger.log(severity['INFO'], 'CREATING BLOB : {}'.format(blob_name))
        
        if self.blob_exists(blob_name):
            logger.log(severity['ERROR'], 'BLOB ALREADY EXISTS: {}'.format(blob_name))
            return operation_status

        try:
            ''' 
            Azure API call to create blob
            '''
            # Instantiate a new BlobClient
            blob_client = self.__container_client.get_blob_client(blob_name)
            
            for chunk in uploaded_file.chunks():
                blob_client.upload_blob(chunk, blob_type=BlobType.BlockBlob)

            #update db
            self.__add_to_db(blob_name)
            operation_status = 1

            #shared_variable.increment_api_call_counter2()
        except Exception as error:
            logger.log(severity['ERROR'], 'BLOB CREATE EXCEPTION: {}'.format(error))

        return operation_status
    
        
    def blob_delete(self, blob_name):
        operation_status = 0
        
        if self.blob_exists(blob_name):
            try:
                ''' 
                # Azure API call to delete blob
                # ''' 
                # Instantiate a new BlobClient
                blob_client = self.__container_client.get_blob_client(blob_name)
                
                # Delete content to blob
                blob_client.delete_blob()
                
                #update blob DB
                self.__delete_from_db(blob_name)
                operation_status = 1
                
                #shared_variable.increment_api_call_counter2()
            except Exception as error:
                logger.log(severity['ERROR'], 'BLOB DELETE EXCEPTION: {}'.format(error))
        else :
            logger.log(severity['ERROR'], 'BLOB NOT FOUND : {}'.format(blob_name))

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
                logger.log(severity['ERROR'], 'BLOB DOWNLOAD EXCEPTION : {}'.format(blob_name))
        else :
            logger.log(severity['ERROR'], 'BLOB NOT FOUND : {}'.format(blob_name))
        return operation_status
    
    
    def delete_all(self):
        blob_list = self.__container_blob_dict[self.__container_name]
        for blob_name in blob_list:
            blob_obj = blob_table.objects.get(blob_name=blob_name, container_name=self.__container_name)        
            blob_obj.delete()
        
        del self.__container_blob_dict[self.__container_name]
        logger.log(severity['INFO'], 'ALL BLOBS DELETED')



class SampleBlob:
    def __init__(self, user_obj, container_client, container_name:str):
        self.__container_client = container_client
        self.__container_name = container_name
        self.__user_obj_info = UserInfo.objects.get(user=user_obj)
    
        self.__container_blob_dict = {
            self.__container_name: set([_.blob_name for _ in blob_table.objects.filter(user_id=self.__user_obj_info.user)])
        }  # dict<str, set()>

        logger.log(severity['INFO'], 'BLOB OBJECT CREATED : {}'.format(self.__container_name))


    def __add_to_dict(self, blob_name:str):
        if not self.blob_exists(blob_name):
            self.__container_blob_dict[self.__container_name].add(blob_name)
        else:
            logger.log(severity['ERROR'], 'BLOB ALREADY PRESENT CANNOT ADD TO DICT : {}'.format(blob_name))


    def __remove_from_dict(self, blob_name:str):
        if self.blob_exists(blob_name):
            self.__container_blob_dict[self.__container_name].remove(blob_name)
        else:
            logger.log(severity['ERROR'], 'BLOB NOT PRESENT CANNOT DELETE FROM DICT : {}'.format(blob_name))


    def __add_to_db(self, blob_name:str):
        new_blob_entry = blob_table()
        
        new_blob_entry.blob_name = blob_name
        new_blob_entry.container_name = self.__container_name
        new_blob_entry.blob_size = 0
        new_blob_entry.blob_update_time = timezone.now()
        new_blob_entry.save()

        # udpate dict
        self.__add_to_dict(blob_name)


    def __delete_from_db(self, blob_name:str):
        blob_obj = blob_table.objects.get(blob_name=blob_name, container_name=self.__container_name)        
        blob_obj.delete()

        #update dict
        self.__remove_from_dict(blob_name)
        logger.log(severity['INFO'], 'BLOB DELETED : {}'.format(blob_name))


    def get_list(self):
        # if self.__container_name in self.__container_blob_dict:
        #     return list(self.__container_blob_dict[self.__container_name])
        # else:
        #     logger.log(severity['ERROR'], 'CONTAINER NOT PRESENT IN DICT : {}'.format(self))
         # Return list of blob dicts for the container
        blobs = blob_table.objects.filter(user_id=self.__user_obj_info.user)
        return [
            {
                'blob_name': b.blob_name,
                'size': b.blob_size,
                'uploaded_at': b.blob_update_time,
                'download_url': f'/download/{b.blob_name}'  # adjust as needed
            }
            for b in blobs
        ]
    

    def blob_exists(self, blob_name:str):
        if self.__container_name in self.__container_blob_dict.keys():
            print(self.__container_blob_dict[self.__container_name])
            print("so : blob_name in self.__container_blob_dict[self.__container_name] ", blob_name in self.__container_blob_dict[self.__container_name])
            return blob_name in self.__container_blob_dict[self.__container_name]
        else:
            logger.log(severity['INFO'], 'BLOB DOES NOT EXIST : {}'.format(blob_name))
            return False


    def blob_create(self, uploaded_file, blob_name):
        operation_status = 0
        
        logger.log(severity['INFO'], 'CREATING BLOB : {}'.format(blob_name))
        
        if self.blob_exists(blob_name):
            logger.log(severity['ERROR'], 'BLOB ALREADY EXISTS: {}'.format(blob_name))
            return operation_status
        
        ''' 
        Azure API call to create blob
        '''
        
        #update db
        self.__add_to_db(blob_name)
        
        return operation_status
    
        
    def blob_delete(self, blob_name):
        operation_status = 0
        
        if self.blob_exists(blob_name):
            ''' 
            # Azure API call to delete blob
            '''
            #update blob DB
            self.__delete_from_db(blob_name)
        else :
            logger.log(severity['ERROR'], 'BLOB NOT FOUND : {}'.format(blob_name))

        return operation_status
    
    
    def download_blob(self, path_to_save, blob_name):
        operation_status = 0
        file_byte_arr = None
        blob_file = os.path.join(path_to_save, blob_name)
        
        if self.blob_exists(blob_name):
            '''
            AZURE API call to download blob
            '''
        else :
            logger.log(severity['ERROR'], 'BLOB NOT FOUND : {}'.format(blob_name))
        return operation_status
    
    
    def delete_all(self):
        blob_list = self.__container_blob_dict[self.__container_name]
        for blob_name in blob_list:
            blob_obj = blob_table.objects.get(blob_name=blob_name, container_name=self.__container_name)        
            blob_obj.delete()
        
        del self.__container_blob_dict[self.__container_name]
        logger.log(severity['INFO'], 'ALL BLOBS DELETED')



        