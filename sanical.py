#!/usr/bin/env python3

import sys, getopt
import datetime
import vobject

def do_sanitize (filename, category=None):
   f = open (filename)
   cal = vobject.readOne (f)
   f.close ()

   for ev in cal.vevent_list:
      try:
         del ev.valarm_list
      except AttributeError:
         pass

      blacklist = ['X-APPLE-STRUCTURED-LOCATION',
                   'X-APPLE-TRAVEL-ADVISORY-BEHAVIOR',
                   'X-LIC-ERROR']

      to_delete = [c for c in ev.getChildren() if c.name in blacklist]
      for c in to_delete:
         ev.remove (c)

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

   cal.prettyPrint()


if __name__ == '__main__':
   optlist, args = getopt.getopt (sys.argv[1:],
                                  'c:', ['category='])

   category = None

   for k, v in optlist:
      if k in ["--category", "-c"]:
         category = v

   for i in args:
      do_sanitize (i, category)

