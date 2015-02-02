#!/usr/bin/env python

from splunklib.modularinput import *
from splunklib.client import Inputs, Service
from azure.servicemanagement.servicemanagementclient import _ServiceManagementClient
import inspect
import requests
import sys
import zipfile

from datetime import date
import logging, traceback
import os

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

class SiteLogService(Script):
    def get_scheme(self):
        scheme = Scheme("Windows Azure Website Logs")
        scheme.use_external_validation = True
        scheme.use_single_instance = False

        subscription_arg = Argument("subscription")
        subscription_arg.data_type = Argument.data_type_string
        subscription_arg.description = "Subscription in which the site lives"
        subscription_arg.required_on_create = True
        scheme.add_argument(subscription_arg)    

        cert_path_arg = Argument("cert-path")
        cert_path_arg.data_type = Argument.data_type_string
        cert_path_arg.description = "Windows Azure Management Cert location"
        cert_path_arg.required_on_create = True
        scheme.add_argument(cert_path_arg)

        site_name_arg = Argument("site-name")
        site_name_arg.data_type = Argument.data_type_string
        site_name_arg.description = "Website to monitor"
        site_name_arg.required_on_create = True    
        scheme.add_argument(site_name_arg)
        return scheme

    def validate_input(self, validation_definition):
        try:
            cert_path = str(validation_definition.parameters["cert-path"])
            site = str(validation_definition.parameters["site-name"])
            subscription = str(validation_definition.parameters["subscription"])
            self.client = _ServiceManagementClient(subscription, cert_path)
            site_resource = self.get_site_resource(site)
        except Exception as e:
            sys.stderr.write("validate_input:" + str(e))

    def stream_events(self, inputs, ew):
        try:
            service = self.get_service(inputs)

            for input_name, input_item in inputs.inputs.iteritems():
                index = str(input_item["index"])
                host = str(input_item["host"])
                cert_path = str(input_item["cert-path"])
                site = str(input_item["site-name"])
                subscription = str(input_item["subscription"])
  
                current_dir = os.path.dirname(__file__)
                log_path = "%s/../logs/%s" % (current_dir, site.lower())
                if not os.path.exists(log_path):
                    os.makedirs(log_path)

                self.client = _ServiceManagementClient(subscription, cert_path)
                log_resource = self.get_log_resource(site)
                self.download_logs(log_resource, log_path)
                self.unzip_and_upload_logs(log_path, site, service, index, host)
 
                event = Event()
                event.stanza = input_name
                event.data = "Logs downloaded at %s" % date.today()
                event.source_type = "website_log_download_status"
                ew.write_event(event)
        except Exception as e:
            sys.stderr.write(str(e) + "\n")

    def get_service(self, inputs):
        server_uri = str(inputs.metadata["server_uri"])
        splunk_port = server_uri[18:]
        session_key = str(inputs.metadata["session_key"])
        args = {'host':'localhost','port':splunk_port,'token':session_key}
        service = Service(**args)
        return service


    def get_site_resource(self, site):
        client = self.client
        webspaces_path = client._get_path("services/webspaces", None)
        # Get the webspaces
        webspaces_resp = client._perform_get(webspaces_path, None)
        webspaces_el = ET.XML(webspaces_resp.body)
        webspace_els = webspaces_el.findall(".//{http://schemas.microsoft.com/windowsazure}Name")
        
        # Loop through each websspace
        for webspace_el in webspace_els:
            try:
                site_path = "%s/%s/sites/%s" % (webspaces_path, webspace_el.text, site)
                # Try to get the site (will fail if it does not exist)
                website_resp = self.client._perform_get(site_path, None)
                break
            except:
                site_path = None

        return site_path

    def get_log_resource(self, site):
        site_path = self.get_site_resource(site)
        client = self.client
        # grab the site configuration
        config_resp = client._perform_get(site_path + "/config", None)
        
        # grab the repo configuration
        repo_resp = client._perform_get(site_path + "/repository", None)

        repo_el = ET.XML(repo_resp.body)
        config_el = ET.XML(config_resp.body)  

        # extract the repo auth info
        user = config_el.findtext(".//{http://schemas.microsoft.com/windowsazure}PublishingUsername")
        pwd = config_el.findtext(".//{http://schemas.microsoft.com/windowsazure}PublishingPassword")
        
        # get the repo url
        repository = repo_el.text

        # create the log resource uri
        logs = repository.replace("https://", "https://%s:%s@" % (user,pwd)) + "dump"
        return logs

    def download_logs(self, log_resource, log_path):
        # get the logs
        logs_resp = requests.get(log_resource);
        chunk_size=32768
        with open("%s/logs.zip" % log_path , 'wb') as fd:
            for chunk in logs_resp.iter_content(chunk_size):
                fd.write(chunk)

    def unzip_and_upload_logs(self, log_path, site, service, index, host):
        # extract logs
        zipfile.ZipFile("%s/logs.zip" % log_path).extractall(log_path)

        inputs = Inputs(service)

        for file in os.listdir(log_path):
            archive_file = "%s/%s.archive" % (log_path, file)
            if not os.path.exists(archive_file):
                source_type = None

                if file.endswith("log.xml"):
                    source_type = "website-deployment"
                elif file.endswith("manifest"):
                    source_type = "website-deployment-manifest"
                elif file.endswith("status.xml"):
                    source_type = "website-deployment-status"
                elif file.endswith(".txt"):
                    source_type = "website-stdout"
                elif file.endswith("trace.xml"):
                    source_type = "website-git-trace"
                elif file.endswith("log"):
                    source_type = "website-iis-log"

                if source_type is not None:
                    self.upload_file("%s/%s" % (log_path, file), inputs, index, host, source_type, archive_file, site)

        for file in os.listdir(log_path):
            if not file.endswith(".archive"):
                try:
                    os.remove("%s/%s" % (log_path, file))
                except:
                    pass

    def upload_file(self, file, inputs, index, host, source_type, archive_file, site):
        args = {'host':host,'index':index,'sourcetype':source_type}
        inputs.oneshot(file, **args)
        with open(archive_file, 'w') as f:
            f.write("")
            f.close()

if __name__ == "__main__":
    sys.exit(SiteLogService().run(sys.argv))





