# Public domain license.
# Author: igor.zavoychinskiy@gmail.com
# Version: 1.1

# A very simple script to produce a .ZIP archive with the product distribution.

import getopt
import json
import logging
import os
import os.path
import re
import shutil
import subprocess
import sys
import time
import collections

ZIP_BINARY = 'L:/Program Files/7-Zip/7z.exe'
PACKAGE_TITLE = 'Surface Mounted Stock-Alike Lights for Self-Illumination'

# SRC configs.
SRC = '..'
# Extract version number from here. See ExtractVersion() method.
#SRC_VERSIONS_FILE = SRC + '/kis.version'
SRC_VERSIONS_FILE = SRC + '/Source/Properties/AssemblyInfo.cs'
# An executable which will be called to build the project's binaraies in
# release mode.
SRC_COMPILE_BINARY_SCRIPT = 'make_binary.cmd'
# Path to the release's binary. If it doesn't exist then no release.
SRC_COMPILED_BINARY = '/Source/bin/Release/SurfaceLights.dll'


# DEST configs.
# A path where releaae structure will be constructed.
DEST = '../Release'
# A path to place resulted ZIP file. It must exist.
DEST_RELEASES = '..'
# A format string which accepts VERSION as argument and return distribution
# file name with no extension.
DEST_RELEASE_NAME_FMT = 'SurfaceLights_v%d.%d.%d'
# A file name format for releases with build field other than zero.
DEST_RELEASE_NAME_WITH_BUILD_FMT = 'SurfaceLights_v%d.%d.%d_build%d'
# The name of the destintation binary.
DEST_VERSIONED_BINARY = '/SurfaceLights.dll'


# Sources to be updated post release (see UpdateVersionInSources).
# All paths must be full.
SRC_REPOSITORY_VERSION_FILE = SRC + '/SurfaceLights.version'


# Destinations to be updated post release (see UpdateVersionInDestinations).
# All paths must be full.
DEST_PLUGIN_VERSION_COPY = (
    SRC_REPOSITORY_VERSION_FILE, DEST
    + '/GameData/SurfaceLights/Plugins/SurfaceLights.version')


# Keys are paths in DEST, values are paths/patterns in SRC.
# When value is a string then the entire source follder is copied.
# Destination folder is not created recursively so, if you need to copy a file
# into "a/b/c" folder then you need three keys: "a", "a/b", and 'a/b/c".
STRUCTURE = collections.OrderedDict({
  '/': [
  ],
  '/GameData' : [],  # This will make the parent folder created.
  '/GameData/SurfaceLights' : [
    '/LICENSE.md',
    '/README.md',
  ],
  '/GameData/SurfaceLights/Plugins' : [
    '/Source/bin/Release/SurfaceLights.dll',
    '/Source/bin/Release/SurfaceLights.xml',
    '/SurfaceLights.version',
    '/Binaries/MiniAVC.dll',
  ],
  '/GameData/SurfaceLights/Parts' : '/Parts',
  '/GameData/SurfaceLights/Patches' : '/Patches',
})

VERSION = None

# Argument values.
MAKE_PACKAGE = False
OVERWRITE_PACKAGE = False


def CopyByRegex(src_dir, dst_dir, pattern):
  for name in os.listdir(src_dir):
    if name == 'CVS':
      continue
    src_file_path = os.path.join(src_dir, name)
    if os.path.isfile(src_file_path) and re.search(pattern, name):
      print 'Copying:', src_file_path
      shutil.copy(src_file_path, dst_dir)


# Makes the binary.
def CompileBinary():
  if not SRC_COMPILED_BINARY is None:
    binary_path = SRC + SRC_COMPILED_BINARY
    if os.path.exists(binary_path):
      os.unlink(binary_path)
  print 'Compiling the sources in PROD mode...'
  code = subprocess.call([SRC_COMPILE_BINARY_SCRIPT])

  if (code != 0
      or not SRC_COMPILED_BINARY is None
      and not os.path.exists(SRC + SRC_COMPILED_BINARY)):
    print 'ERROR: Compilation failed.'
    exit(code)


# Purges any existed files in the release folder.
def CleanupReleaseFolder():
  print 'Cleanup release folder...'
  shutil.rmtree(DEST, True)


# Creates whole release structure and copies the required files.
def MakeFoldersStructure():
  print 'Make release folders structure...'
  folders = sorted(STRUCTURE.keys())
  # Make.
  for folder in folders:
    dest_path = DEST + folder 
    sources = STRUCTURE[folder]
    if not isinstance(sources, list):
      src_path = SRC + sources
      print 'Copying folder "%s" into "%s"' % (src_path, dest_path)
      shutil.copytree(src_path, dest_path)
    else:
      print 'Making folder "%s"' % dest_path
      os.mkdir(DEST + folder)
      for file_path in STRUCTURE[folder]:
        source_path = SRC + file_path
        if file_path.endswith('/*'):
          print 'Copying files "%s" into folder "%s"' % (
              source_path, dest_path)
          CopyByRegex(SRC + file_path[:-2], dest_path, '.+')
        else:
          print 'Copying file "%s" into folder "%s"' % (source_path, dest_path)
          shutil.copy(source_path, dest_path)


# Extarcts version number of the release from the sources.
def ExtractVersion():
  global VERSION
  with open(SRC_VERSIONS_FILE) as f:
    content = f.readlines()
  for line in content:
    if line.lstrip().startswith('//'):
      continue
    # Expect: [assembly: AssemblyVersion("X.Y.Z")]
    print line
    matches = re.match(
        r'\[assembly: AssemblyVersion.+?\("(\d+)\.(\d+)\.(\d+)(.(\d+))?"\)\]',
        line)
    if matches:
      VERSION = (int(matches.group(1)),  # MAJOR
                 int(matches.group(2)),  # MINOR
                 int(matches.group(3)),  # PATCH
                 int(matches.group(5) or 0))  # BUILD, optional.
      break
      
  if VERSION is None:
    print 'ERROR: Cannot extract version.'
    exit(-1)
  print 'Releasing version: v%d.%d.%d build %d' % VERSION


# Updates the destination files with the version info.
def UpdateVersionInDestinations():
  print 'Copy plugin version file "%s" into "%s"' % (
      DEST_PLUGIN_VERSION_COPY[0], DEST_PLUGIN_VERSION_COPY[1])
  shutil.copy(DEST_PLUGIN_VERSION_COPY[0], DEST_PLUGIN_VERSION_COPY[1])


# Updates the source files with the version info.
def UpdateVersionInSources():
  print 'Update repository version file:', SRC_REPOSITORY_VERSION_FILE
  UpdateVersionInJsonFile_(SRC_REPOSITORY_VERSION_FILE)


def UpdateVersionInJsonFile_(name):
  with open(name) as fp:
    content = json.load(fp);
  if not 'VERSION' in content:
    print 'ERROR: Cannot find VERSION in:', name
    exit(-1)
  content['VERSION']['MAJOR'] = VERSION[0]
  content['VERSION']['MINOR'] = VERSION[1]
  content['VERSION']['PATCH'] = VERSION[2]
  content['VERSION']['BUILD'] = VERSION[3]
  with open(name, 'w') as fp:
    json.dump(content, fp, indent=4, sort_keys=True)


def MakeReleaseFileName():
  if VERSION[3]:
    return DEST_RELEASE_NAME_WITH_BUILD_FMT % VERSION
  else:
    return DEST_RELEASE_NAME_FMT % VERSION[:3]


# Creates a package for re-destribution.
def MakePackage():
  if not MAKE_PACKAGE:
    print 'No package requested, skipping.'
    return

  release_name = MakeReleaseFileName();
  package_file_name = '%s/%s.zip' % (DEST_RELEASES, release_name)
  if os.path.exists(package_file_name):
    if not OVERWRITE_PACKAGE:
      print 'ERROR: Package for this version already exists.'
      exit(-1)

    print 'WARNING: Package already exists. Deleting.'
    os.remove(package_file_name)

  print 'Making %s package...' % PACKAGE_TITLE
  code = subprocess.call([
      ZIP_BINARY,
      'a',
      package_file_name,
      DEST + '/*'])
  if code != 0:
    print 'ERROR: Failed to make the package.'
    exit(code)


def main(argv):
  global MAKE_PACKAGE, OVERWRITE_PACKAGE, VERSION

  try:
    opts, _ = getopt.getopt(argv[1:], 'dpo', )
  except getopt.GetoptError:
    print 'make_release.py [-d]'
    exit(2)
  opts = dict(opts)
  MAKE_PACKAGE = '-p' in opts
  OVERWRITE_PACKAGE = '-o' in opts

  ExtractVersion()
  CompileBinary()
  CleanupReleaseFolder()
  MakeFoldersStructure()
  UpdateVersionInSources()
  UpdateVersionInDestinations()
  MakePackage()
  print 'SUCCESS!'

main(sys.argv)
