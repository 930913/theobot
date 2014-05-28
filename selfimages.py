#! /usr/bin/env python

from __future__ import unicode_literals
import sys
import time
import os
import cStringIO
import re
import json
import urllib2

import mwclient
import mwparserfromhell
import requests

from PIL import Image
from PIL.ExifTags import TAGS

from theobot import password
from theobot import bot

# CC-BY-SA Theopolisme

def main():
	global site
	site = mwclient.Site('en.wikipedia.org')
	site.login(password.username, password.password)

	global donenow
	donenow = 0

	category = mwclient.listing.Category(site, 'Category:Self-published work')
	for page in category:
		if page.namespace == 6 and "description" not in site.expandtemplates(text=page.edit()).lower():
			process_page(page)
		else:
			pass

def get_exif_date(image):
	"""Given a filename, downloads the file, gets its
	EXIF creation date, and returns it.
	"""
	try:
		response = requests.get(image.imageinfo['url'])
	except AttributeError:
		return None # It wasn't even a file to begin with

	imageobj = cStringIO.StringIO(response.content)

	result = None
	try:
		i = Image.open(imageobj)
		info = i._getexif()
		for tag, value in info.items():
			if result == None:
				decoded = TAGS.get(tag, tag)
				if decoded == "DateTime":
					result = time.strptime(value, "%Y:%m:%d %H:%M:%S")
					result = time.strftime("%d %B %Y",result)
					break
	except:
		pass # This means that the image didn't have any EXIF data

	return result

def process_page(page):
	"""Given an image object, gets its uploader and
	its upload date, fills in {{Information}} for it,
	and saves the new page.
	"""
	revision =  page.revisions(dir='newer').next()

	user = revision['user']

	date = get_exif_date(page)
	if date == None:
		date = time.strftime("%d %B %Y",revision['timestamp'])

	contents = page.edit()

	if contents != "":
		description = contents.strip()
		desc_code = mwparserfromhell.parse(description)
		for bad_code in desc_code.ifilter_templates(): # Remove templates
			description = description.replace(unicode(bad_code),'')
		for bad_code in desc_code.ifilter_headings(): # Remove headers
			description = description.replace(unicode(bad_code),'')
		if description.find('<nowiki') != -1:
			return # Skip complex descriptions
		description = description.replace('|','{{!}}') # Escape pipe symbols
		description = re.sub(r"""[ ]{2,}"""," ",description,flags=re.U) # Remove excessive spaces
		description = re.sub(r"""\[\[(?:File|Image):(.*?)(?:\|.*?)\]\]""",r"[[:File:\1]]",description,flags=re.U) # Turn images into links
		description = re.sub(r"""\[\[User:.*?\]\] \(\[\[User talk:J.*?\]\]\).*?\(UTC\)""",'',description,flags=re.U) # Remove signatures when possible
	else:
		description = ""
	
	### Fetch image captions used, and list them if exist | A930913 for Sfan00_IMG ###
	data=json.load(urllib2.urlopen("http://tools-webproxy/cluestuff/cgi-bin/vada/imgcaps.py?img={name}".format(**page)))
	if len(data): description="* This page: "+description+"\n"+"".join(["* [["+k+"]]: "+data[k]+"\n" for k in data])																																																																																									
	
	contents = u"""{{Information
| description = """+description+"""
| source      = {{own}}
| date        = """ + unicode(date) + """
| author      = {{subst:usernameexpand|""" + user.replace(" ","_") + """}}
}}\n""" + contents

	global donenow
	if bot.donenow("User:Theo's Little Bot/disable/selfimages",donenow=donenow,donenow_div=5,shutdown=100) == True:
		# adding the template
		page.save(contents,"[[WP:BOT|Bot]]: Automatically adding {{[[Template:Information|Information]]}} to self-published work) ([[User:Theo's Little Bot/disable/selfimages|disable]]")
		donenow += 1
		# notifying the uploader
		usertalktitle = "User talk:"+user
		if bot.nobots(usertalktitle,user="Theo's Litle Bot",task='selfimages') == True:
			usertalk = site.Pages[usertalktitle]
			notification = "\n\n== Notification of automated file description generation ==\n{{subst:Un-botfill|file="+page.page_title+"|sig=~~~~}}"
			usertalk.save(appendtext=notification,"[[WP:BOT|Bot]]: Notifying user about autogenerated {{[[Template:Information|Information]]}} addition) ([[User:Theo's Little Bot/disable/selfimages|disable]]",redirect=True)
	else:
		sys.exit()

if __name__ == '__main__':
	main()
