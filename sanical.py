#!/usr/bin/env python3

import sys, getopt
import datetime
import vobject

def do_sanitize (filename, outfile=None, category=None):
   f = open (filename)
   cal = vobject.readOne (f)
   f.close ()

   for ev in cal.vevent_list:
      try:
         del ev.valarm_list
      except AttributeError:
         pass

      try:
         del ev.attendee_list
      except AttributeError:
         pass

      blacklist = ['X-APPLE-STRUCTURED-LOCATION',
                   'X-APPLE-TRAVEL-ADVISORY-BEHAVIOR',
                   'X-BUSYMAC-LASTMODBY',
                   'X-LIC-ERROR',
                   'X-MICROSOFT-CDO-APPT-SEQUENCE',
                   'X-MICROSOFT-CDO-ALLDAYEVENT',
                   'X-MICROSOFT-CDO-BUSYSTATUS',
                   'X-MICROSOFT-CDO-IMPORTANCE',
                   'X-MICROSOFT-CDO-INSTTYPE',
                   'X-MICROSOFT-CDO-INTENDEDSTATUS',
                   'X-MICROSOFT-CDO-OWNERAPPTID',
                   'X-MICROSOFT-DISALLOW-COUNTER']

      to_delete = [c for c in ev.getChildren() if c.name in blacklist]
      for c in to_delete:
         ev.remove (c)

      try:
         del ev.description.params["ALTREP"]
      except (KeyError, AttributeError):
         pass

      try:
         startdate = ev.dtstart.value
         enddate   = ev.dtend.value
         delta = datetime.timedelta (days=1)

         if (startdate.date() + delta == enddate.date() and
             enddate.time().hour <= 8):
            ev.dtend.value = datetime.datetime (enddate.year,
                                                enddate.month,
                                                enddate.day,
                                                0, 0, 0, 0,
                                                enddate.tzinfo)

      except AttributeError:
         pass

      if category:
         try:
            cats = ev.categories.value
         except AttributeError:
            ev.add ("categories")
            cats = []

       # if category not in cats:
       #    cats.append (category)

         cats = [category]

         ev.categories.value = cats

   if outfile:
      f = open (outfile, "w")
      f.write (cal.serialize ())
      f.close ()
   else:
      print (cal.serialize ())


if __name__ == '__main__':
   optlist, args = getopt.getopt (sys.argv[1:],
                                  'c:o:i', ['category=', 'outfile=', 'inplace'])

   category = None
   outfile = None
   inplace = False

   for k, v in optlist:
      if k in ["--category", "-c"]:
         category = v
      elif k in ["--outfile", "-o"]:
         outfile = v
      elif k in ["--inplace", "-i"]:
         inplace = True

   for i in args:
      if inplace:
         outfile = i
      do_sanitize (i, outfile, category)

