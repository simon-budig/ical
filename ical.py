#!/usr/bin/env python3
# -*- coding:utf8 -*-

# liest den Kalender von HaSi. Bei Fragen bitte an Simon wenden.
#
# python ical.py --summary  -- Terminübersicht mit Links auf die Kalenderseite
# python ical.py --full     -- Terminübersicht mit Beschreibungen
#
# Wenn keine URLs zu icals angegeben werden dann wird die URL des
# HaSi-Kalenders genutzt.

import sys, io, subprocess, re, urllib.request
import datetime
import dateutil.rrule, dateutil.parser, dateutil.tz
import uuid
import cgi, markdown

default_url = "file:///home/simon/src/ical/basic.ics"
default_url = "https://calendar.google.com/calendar/ical/bhj0m4hpsiqa8gpfdo8vb76p7k%40group.calendar.google.com/public/basic.ics"
default_url = "https://cloud.hackspace-siegen.de/calendar/hasi/master/"

hasi_format = """\
<div class="event">
  <div class="date" class="center">
    <span class="center">
      <span class="bubble-event-day">{datetime:%a}</span>
      <span class="bubble-event-date">{datetime:%d.%m.}</span>
    </span>
  </div>
  {image:<div class="event-image" style="background-image: url(%s)"></div>}
  <div class="event-main">
    {summary:html:<h2>%s</h2>}
    <p class="event-time-place">
      <i class="fa fa-clock-o event-icon"></i> {datetime:%Y-%m-%d %H:%M}
      {location:html:<br><i class="fa fa-map-marker event-icon"></i> %s}
    </p>
    {description:md:%s}
    {follow_ups:html:<p><em>Folgetermine:</em> %s</p>}
  </div>
</div>\
"""



calendars = {}

# figure out the day start in local time
now = datetime.datetime.now (dateutil.tz.tzlocal ())
now = now.replace (hour=0, minute=0, second=0, microsecond=0)
now = now.astimezone (dateutil.tz.tzutc ())


def kramdown (input):
   p = subprocess.Popen ("kramdown",
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
   out, err = p.communicate (input.encode ('utf-8'))
   # ignoring errors here, might be a problem. But all entries are
   # concatenated so we can't pinpoint the errors to specific calendar entries
   return out.decode ('utf-8')



def simple_tzinfos (abbrev, offset):
   if not abbrev and not offset:
      return dateutil.tz.tzlocal ()
   elif abbrev == "UTC" and offset == 0:
      return dateutil.tz.tzutc ()
   else:
      print ("simple_tzinfos:", abbrev, offset)
   return 0



class FmtString (str):
   def __format__ (self, format_spec):
      if not self or not format_spec:
         return self

      if format_spec[:5] == "html:":
         return format_spec[5:] % cgi.escape (self)
      elif format_spec[:3] == "md:":
         return format_spec[3:] % markdown.markdown (self, safe_mode="escape")
      else:
         return format_spec % self



class Event (dict):
   def __init__ (self, entries):
      for k, v in entries.items ():
         self[k] = v
      self.upd = None


   def set_update_events (self, updates):
      if len (updates) > 0:
         self.upd = updates[0]
         self.upd.set_update_events (updates[1:])


   def shortdesc (self):
      r = []
      tim, evt = self.get_time ()[0]

      if evt["SUMMARY"]:
        r.append ("* __%s:__ <a name=\"summary-%s\" href=\"/calendar/#item-%s\">%s</a>" % (str (tim.strftime ("%d. %m. %Y")),
                                                                                        evt["UID"], evt["UID"], evt["SUMMARY"]))

      return "\n\n".join (r) + "\n"


   def longdesc (self):
      r = []
      tim, evt = self.get_time ()[0]
      if evt["SUMMARY"]:
         r.append ("## <a name=\"item-%s\" href=\"/calendar/#summary-%s\">%s</a>" % (evt["UID"], evt["UID"], evt["SUMMARY"]))

      r.append (str (tim.strftime ("__%d. %m. %Y, %H:%M Uhr__")) + "\n")
      if evt["DESCRIPTION"]:
         r.append (evt["DESCRIPTION"] + "\n")

      if evt["LOCATION"]:
         r.append ("_Ort:_ " + evt["LOCATION"])

      if evt["URL"]:
         r.append ("_weitere Infos:_ [%s](%s)" % (evt["URL"], evt["URL"]))

      pending = self.get_time ()[1:]
      if pending:
         r.append ("_Folgetermine:_ " +
                   ", ".join ([p[0].strftime ("%d. %m. %Y")
                              for p in pending[:3]]) + [".", "…"][len (pending) > 3])
      return "\n\n".join (r) + "\n"


   def get_ical (self, filter=None):
      pass


   def __getitem__ (self, key):
      val = super (Event, self).get (key, None)
      if val == None:
         tim, evt = self.get_time ()[0]
         if key == 'datetime':
            val = tim
         elif key == 'summary':
            val = FmtString (evt["SUMMARY"])
         elif key == 'description':
            val = FmtString (evt["DESCRIPTION"])
         elif key == 'location':
            val = FmtString (evt["LOCATION"])
         elif key == 'image':
            val = FmtString ("")
         elif key == 'follow_ups':
            val = ""
            pending = self.get_time ()[1:]
            if pending:
               val = ", ".join ([p[0].strftime ("%d. %m. %Y")
                                 for p in pending[:3]]) + [".", "…"][len (pending) > 3]
            val = FmtString (val)

      return val


   def __setitem__ (self, key, value):
      rdict = { 'n' : "\n" }
      value = re.sub ("\\\\(.)",
                      lambda x: rdict.get (x.group (1), x.group (1)), value)
      super (Event, self).__setitem__ (key, value)


   def __lt__ (self, other):
      owntimes = self.get_time ()
      othertimes = other.get_time ()

      if len (owntimes) > 0 and len (othertimes) > 0:
         return self.get_time ()[0][0] < other.get_time ()[0][0]
      elif len (othertimes) > 0:
         return True
      elif len (owntimes) > 0:
         return False
      else:
         return False


   def is_pending (self):
      owntimes = self.get_time ()

      if len (owntimes):
         return now < self.get_time ()[0][0]
      else:
         return False


   def get_time (self, times = []):
      if "RECURRENCE-ID" in self:
         rec = dateutil.parser.parse (self["RECURRENCE-ID"],
                                      tzinfos = simple_tzinfos)
         times = [t for t in times if t[0] != rec]

      if "DTSTART" in self and "RRULE" in self:
         rr = dateutil.rrule.rrulestr (self.rrtext, tzinfos = simple_tzinfos)
         pending = rr.between (now, now + datetime.timedelta (120))
         times = times + [ (p.astimezone (dateutil.tz.tzlocal ()), self)
                           for p in pending ]

      elif "DTSTART" in self:
         dts = dateutil.parser.parse (self["DTSTART"], tzinfos = simple_tzinfos)
         times = times + [ (dts.astimezone (dateutil.tz.tzlocal ()), self) ]

      else:
         times = times + [ (now.astimezone (dateutil.tz.tzlocal ()), self) ]

      if self.upd:
         times = self.upd.get_time (times)

      times.sort ()
      while len (times) > 1 and times[0][0] < now:
         times = times[1:]

      return times



class Calendar (object):
   def __init__ (self, url=None):
      if not url:
         url = default_url

      self.url = url

      data = urllib.request.urlopen (self.url).read ()
      data = data.decode ('utf-8')

      # normalize lineends
      data = data.replace ("\r\n", "\n")
      data = data.replace ("\n\r", "\n")
      # ical continuation lines
      data = data.replace ("\n ", "")

      lines = [l.strip () for l in data.split ("\n")]

      self.eventdict = {}
      cur_event = None
      inhibit = None
      raw_rrtext = ""

      for l in lines:
         if not l:
            continue

         extra = None
         key, value = l.split (":", 1)

         if ";" in key:
            key, extra = key.split (";", 1)

         if key == "BEGIN" and value == "VEVENT":
            cur_event = {}
            raw_rrtext = ""
            continue
         elif key == "BEGIN":
            inhibit = value

         if key in ["RRULE", "RRULE", "RDATE", "EXRULE", "EXDATE", "DTSTART"]:
            raw_rrtext = raw_rrtext + "%s:%s\n" % (key, value)

         if key == "END" and value == "VEVENT":
            if "UID" not in cur_event:
               cur_event["UID"] = "%s" % uuid.uuid1 ()
            uid = cur_event["UID"]
            if uid not in self.eventdict:
               self.eventdict[uid] = []
            self.eventdict[uid].append (Event (cur_event))
            self.eventdict[uid][-1].rrtext = raw_rrtext
            cur_event = None
            continue
         elif key == "END" and value == inhibit:
            inhibit = None

         if cur_event != None and inhibit != None:
            cur_event[key] = value

      self.eventlist = []

      for id, ev in self.eventdict.items ():
         ev.sort (key = lambda x: int (x.get ("SEQUENCE", "0")))
         ev[0].set_update_events (ev[1:])
         self.eventlist.append (ev[0])

      self.eventlist.sort ()


   def get_summary (self, limit=-1):
      el = [ e for e in self.eventlist if e.is_pending () ]
      if limit > 0:
         el = el[:limit]
      summary  = "\n".join ([e.shortdesc () for e in el])
      return kramdown (summary)


   def get_fulllist (self, limit=-1):
      el = [ e for e in self.eventlist if e.is_pending () ]
      if limit > 0:
         el = el[:limit]
      summary  = "\n".join ([e.longdesc () for e in el])
      return kramdown (summary)


   def get_formatted (self, template, limit=-1):
      el = [ e for e in self.eventlist if e.is_pending () ]
      if limit > 0:
         el = el[:limit]
      text  = "\n".join ([template.format_map (e) for e in el])
      return text



def ical_replace (m):
   args   = m.group (2).split ()
   format = "summary"
   limit  = -1
   url    = default_url

   if len (args) >= 1:
      if ":" in args[0]:
         format, limit = args[0].split (":", 2)
         limit = int (limit)
      else:
         format = args[0]

   if len (args) >= 2:
      url = args[1]

   if not calendars.has_key (url):
      calendars[url] = Calendar(url)

   if format == "full":
      txtdata = calendars[url].get_fulllist (limit)
   else:
      txtdata = calendars[url].get_summary (limit)

   return m.group(1) + txtdata + m.group(3)



if __name__ == '__main__':
   if not sys.argv[1:]:
      c = Calendar ()
      # print (c.get_fulllist ())
      print (c.get_formatted (hasi_format))

   for f in sys.argv[1:]:
      data = open (f).read ()
      data2 = re.sub (r'(?ims)(<!--\s*ical\b\s*(.*?)\s*-->).*?(<!--\s*/ical\s*-->)',
                      ical_replace, data)

      if data2 != data:
         outf = open (f, "w")
         outf.write (data2)
         outf.close ()

