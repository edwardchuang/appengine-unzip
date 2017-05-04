# -*- coding: utf-8 -*-
import cloudstorage as gcs
import webapp2
import re
import os
import json
import google.appengine.ext.blobstore as blobstore
import google.appengine.api.images as images
from mimetypes2 import mimetypes2
from google.appengine.ext.webapp import blobstore_handlers
import StringIO
import zipfile

class PrepareUpload(webapp2.RequestHandler):
  def get(self):
    ret = blobstore.create_upload_url('/_ah/callbackUpload', gs_bucket_name='*CHANGEME*')
    self.response.headers['cache-control'] = 'no-cache'
    self.response.headers['content-type'] = 'text/plain'
    self.response.write(ret)

class CallbackUpload(blobstore_handlers.BlobstoreUploadHandler):
  def processUnzip(self, filepath, gcs_path, filename):
    mime = mimetypes2()
    tmpzip = gcs.open(filepath).read()
    objzip = zipfile.ZipFile(StringIO.StringIO(tmpzip), 'r')
    zip_files = []
    for file in objzip.namelist():
      ext = os.path.splitext(file)[1]
      content_type = mime.guess(ext) or 'application/octet-stream'
      target_path = os.path.join(gcs_path, file)
      gcs_new = gcs.open(target_path, 'w', content_type)
      z = objzip.open(file)
      gcs_new.write(z.read())
      gcs_new.close()
      zip_files.append(file)
    gcs.delete(filepath)
    self.response.headers['cache-control'] = 'no-cache'
    self.response.headers['content-type'] = 'text/javascript'
    self.response.write(json.dumps({"zip_file": filename, "unzip_files" : zip_files, "path": gcs_path}))
    return

  def post(self):
    file_info = self.get_file_infos()[0]
    path = self.request.get('path') or '/'
    if '/' == path[0]:
      path = path[1:]
    new_path = os.path.join('/*CHANGEME*', path)
    if True == zipfile.is_zipfile(file_info.filename):
      return self.processUnzip(file_info.gs_object_name[3:], new_path, file_info.filename)
      # NOTREACHED
    gcs.copy2(file_info.gs_object_name[3:], os.path.join(new_path, file_info.filename), {'content-type': file_info.content_type})
    gcs.delete(file_info.gs_object_name[3:]) # remove leading /gs
    rtn_data = {
      "gs_object_name": new_path,
      "content_type": file_info.content_type,
      "size": file_info.size,
      "md5_hash": file_info.md5_hash,
      "filename": file_info.filename
    }
    self.response.headers['cache-control'] = 'no-cache'
    self.response.headers['content-type'] = 'text/javascript'
    self.response.write(json.dumps(rtn_data))

app = webapp2.WSGIApplication([
  ('/_ah/prepareUpload', PrepareUpload),
  ('/_ah/callbackUpload', CallbackUpload),
], debug=True)
