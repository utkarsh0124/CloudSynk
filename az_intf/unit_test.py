#####################################################################
#                             WARNING!                              #
#                                                                   #
#       Run this file only with azure portal opened alongside       #
#       Create/delete functions call Paid AZURE APIs                # 
#       call functions before cross checking the portal             #
#                                                                   #
#                         CODE SENSIBLY !!!!                        #
#####################################################################


from db_user import DbUser
from api_utils import Auth, Container
import shared_variable

import os

def total_api_calls():
    print("\n\n=========================")
    print("TOTAL API CALLS   : ", shared_variable.AZURE_API_CALL_COUNT)
    print("=========================")


def delete_container(ctr):
    print("DELETING CONTAINER")
    ctr.container_delete()

def add_container(ctr):
    print("CREATING CONTAINER")
    ctr.container_create()


def delete_blob(blob_obj, blob_name):
    print("DELETING BLOB")
    blob_obj.blob_delete(blob_name)

def add_blob(blob_obj, blob_path):
    print("CREATING BLOB")
    blob_obj.blob_create(blob_path)    


if __name__ == '__main__':
    user_obj = DbUser.DbUser()
    
    print("Authenticating user locally")
    if user_obj.user_auth_local():
        
        print("ESTABLISHING CONNECTION TO AZURE")
        azure_conn = Auth.Auth()
        
        client = azure_conn.auth_api()
        print("SUCCESS")

        #--------------- CONTAINER ---------------#

        #Do not remove 'admin-container' --> for testing purpose
        # Container Object
        ctr_id = "container1"
        ctr = Container.Container(ctr_id, client)


        ###################################################################
        #   add containers that are already present in azure portal
        ###################################################################
        
        ctr.container_list.add("admin-container")
        ctr.container_list.add("container1")
        
        ###################################################################


        print(ctr.container_list)
        add_container(ctr)
        # delete_container(ctr)
        print(ctr.container_list)
        
        #------------------------------------------#



        #------------------ BLOB ------------------#
        
        #Blob Object
        blob_obj = ctr.blob()
        
        ##################################################################
        #   add Blobs that are already present
        ##################################################################
        # blob_obj.blob_list.add('blob1.txt')
        # blob_obj.blob_list.add('blob2.txt')
        ##################################################################

        
        blob_path = os.path.join('/workspace','storageWksp','StorageApp','az_intf')
        print("Blob Path : ", os.path.join(blob_path,"blob1.txt"))
        print("Blob Path : ", os.path.join(blob_path,"blob2.txt"))
        print("Blob list : ", blob_obj.get_list())
        
        add_blob(blob_obj, os.path.join(blob_path,"blob1.txt"))
        add_blob(blob_obj, os.path.join(blob_path,"blob2.txt"))
        
        print("Blob list : ", blob_obj.get_list())

        # delete_blob(blob_obj, 'blob1.txt')
        # delete_blob(blob_obj, 'blob2.txt')
        
        print("DOWNLOADING BLOB1 and Blob2")
        # blob_path_download = os.path.join('/workspace','storageWksp','StorageApp')
        # blob1 = blob_obj.download_blob(blob_path_download, 'blob1.txt')
        # blob2 = blob_obj.download_blob(blob_path_download, 'blob2.txt')
        
        print("DELETING CONTAINER : container1")
        ctr.container_delete()  

        total_api_calls()

        # del blob
        # del ctr