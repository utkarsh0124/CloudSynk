from user import user
from azure_api import azure_auth, blob, container
import shared_variable

import os

def total_api_calls():
    print("\n\n=========================")
    print("TOTAL API CALLS   : ", shared_variable.AZURE_API_CALL_COUNT)
    print("=========================")


if __name__ == '__main__':
    user_obj = user.User()
    
    print("Authenticating user locally")
    if user_obj.user_auth_local():
        
        print("ESTABLISHING CONNECTION TO AZURE")
        azure_conn = azure_auth.Azure_auth()
        
        client = azure_conn.azure_auth()
        print("SUCCESS")
        
        ctr = container.Container(client)
        
        ctr_id = "container1"
        print("CREATING CONTAINER")
        ctr.container_create(ctr_id)
        
        # print("CHECKING CONTAINER EXISTS")
        # print("container1 exists : ", ctr.container_exists(ctr_id))
        # print("container2 exists : ", ctr.container_exists("container2"))

        # ctr_list = ctr.get_list()
        # print(ctr_list)
        
        # blob = ctr.blob(ctr_id)
        
        # blob_path = os.path.join("C:\\Users\\utkar\\Desktop\\azure_storage\\intf")
        
        # print("CREATING BLOB")
        # blob.blob_create(blob_path, "blob1.txt")
        # blob.blob_create(blob_path, "blob2.txt")
        # blob.blob_create(blob_path, "blob3.txt")
        # blob.blob_create("blob4.txt")
        
        # blob_list = blob.get_list()
        # print(blob_list)
        
        # print("blob1 Exists : ", blob.blob_exists("blob1.txt"))
        # print("blob2 Exists : ", blob.blob_exists("blob2.txt"))
        
        # print("DOWNLOADING BLOB1 and Blob2")
        # blob1 = blob.download_blob(blob_path, 'blob1.txt')
        # blob2 = blob.download_blob(blob_path, 'blob2.txt')
        # blob2 = blob.download_blob(blob_path, 'blob3.txt')
        
        # print(blob1)
        # print(blob2)
        
        # blob1_file.write(blob1)
        # blob2_file.write(blob2)
       
        # blob1_file.close()
        # blob2_file.close()
        
        # print("DELETING blob1 and blob2") 
        # blob.blob_delete("blob1.txt")
        # blob.blob_delete("blob2.txt")
        # blob.blob_delete("blob3.txt")
       
        # print("DELETING CONTAINER : container1")
        # ctr.container_delete(ctr_id)  

        total_api_calls()

        # del blob
        # del ctr 