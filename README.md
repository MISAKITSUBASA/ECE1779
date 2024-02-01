# ECE1779

This course provides an introduction into the technologies behind cloud computing. A
combination of lectures and hands-on programming assignments expose the student to the leading
cloud computing paradigms and programming interfaces (e.g., EC2, Lambda). In addition,
lectures provide an overview of the underlying technological concepts that make cloud computing
possible (e.g., virtualization, scalability, fault tolerance, security).

Our application is an online image storage system. This system allows users to upload their images for storage in order to save local storage space. lt also notifies the user by email through Amazon SES when a user exceeds the storage limit. The user is able to download the image he uploads, view the images online as well as organize the images he uploads by grouping them into albums through Amazon Rekognition. There is also a cache assigned to the user in order to speed up the process of retrieving images. The user is able to configure the cache size as well as the replacement policy. Our online storage system ensures that each user can only view and manage the images in his own account after logging in by applying Amazon Cognito.
