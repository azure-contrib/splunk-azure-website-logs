splunk-azure-website-logs
=========================

App for downloading Windows Azure Website diagnostic data into Splunk.

Disclaimer: This is currently a personal project / not supported :-)

![screenshot](https://dl.dropboxusercontent.com/u/6860088/splunk%20screeshot.png)

# What is does

This Splunk application will download all of your Windows Azure Website diagnostic data into Splunk on a continual basis.

# How to install it.

* Create an application folder in your $SPLUNK_HOME$/ directory i.e. 'azure-website-logs'
* Copy the repo files into this new folder.
* Copy your Windows Azure Management certificate into a folder such as a folder relative to the application.

# Configuring

* Launch Splunk. If it was already running, you will need to restart your instance in order to pick up the app.
* You should see the "Windows Azure Website Logs" app show up on the main dashboard. 
* Click on "Manage Inputs" under "Data"
* Click on "Windows Azure Website Logs"
* Click "New". A dialog will pop up fro configuring your new input.
* Enter in your subscription id (you can get this from the Windows Azure portal or command line tools)
* Enter in the path for your management certificate.
* Enter the website to monitor.
* Click "More settings"
* Specify the interval to the number of seconds you want Splunk to wait between each poll.
* Click "Save" in order to save the new input.

Now that your input is enabled you should start to see logs pouring in.

# Log source types.

As Splunk ingests website logs it will create data using the following sourcetypes.

* website-deployment: Log of deployment script execution 
* website-deployment-manifest: Detailed list of files that were picked up.
* website-deployment-status: Summary data for each deployment. 
* website-stdout: Console output, if enabled.
* website-git-trace: Log for git operations performed related to the git enpoint. 
* website-iis-log: HTTP traffic for the website. This will only be present if site logging is enabled.
* azure_website_logs: Record of when the last poll occurred / if it succeeded.

The following query in Splunk will show you all the logs by count: 

```
sourcetype=*website* | stats count by sourcetype
```

# How it works behind the scenes.
This application includes a modular input written in Python which connects to Windows Azure using the Azure Python SDK to download the logs. 

It receives a zip file, extracts all the logs and then loads them up into Splunk by calling the Splunk `OneShot` API in the Python SDK.

For each file uploaded, an .archive file is created (0 byte file with the same filename with an .archive extension). On subsequent polls, only files that do not have an .archive
file present will be uploaded.

# Known issues
* Some logs are not being correctly handled as once the file is uploaded, the same file will be ignored even if the file contents change.
* Currently this does not work properly on Windows due to a path issue related to extracting zip files with folders, but this will be fixed shortly.



