#!/bin/bash

# This script generates the folder hierarchy for a new organisation.

if [[ $# -ne 1 ]] ; then
  echo "Usage: $0 <orgname>" >&2
  exit 1
fi

ORGANAME=$1
ORGA=${ORGANAME,,}
COLOR=aaccff

# as of yet unused
HI_COLOR=$(COLOR)
MID_COLOR=`printf  "%02x%02x%02x" $(( (0x${COLOR:0:2} * 2 + 1 * 255 + 1) / 3 )) $(( (0x${COLOR:2:2} * 2 + 1 * 255 + 1) / 3 )) $(( (0x${COLOR:4:2} * 2 + 1 * 255 + 1) / 3 ))`
LO_COLOR=`printf  "%02x%02x%02x" $(( (0x${COLOR:0:2} * 1 + 2 * 255 + 1) / 3 )) $(( (0x${COLOR:2:2} * 1 + 2 * 255 + 1) / 3 )) $(( (0x${COLOR:4:2} * 1 + 2 * 255 + 1) / 3 ))`

if [[ ${ORGA} =~ ^.*-edit$ ]] ; then
  echo "<orgname> must not end in \"-edit\"" >&2
  exit 1
fi

# workaroud for "[a-z]" matching umlauts.

LETTER="[abcdefghijklmnopqrstuvwxyz]"
LETNUM="[abcdefghijklmnopqrstuvwxyz0-9-]"

if [[ ! ${ORGA} =~ ^${LETTER}${LETNUM}*$ ]] ; then
  echo "<orgname> is invalid. Please use [a-z][-a-z0-9]* only" >&2
  exit 1
fi


DEST=collections/collection-root

if [[ ! -d ${DEST} ]] ; then
  echo "Please start this script in the folder containing \"${DEST}\"" >&2
  exit 1
fi


if [[ -d ${DEST}/${ORGA} ]] ; then
  echo "Orgname \"${ORGA}\" already exists. Please choose a different one."
  exit 1
fi


# readonly calendars

mkdir -m 0750 -p ${DEST}/${ORGA}

for calname in All Events Highlights ; do
  cal=${calname,,}
  mkdir -m 0750 -p ${DEST}/${ORGA}/${cal}

  echo "{\"C:calendar-description\": \"${ORGANAME}-${calname}\", \"C:supported-calendar-component-set\": \"VEVENT,VJOURNAL,VTODO\", \"D:displayname\": \"${ORGANAME} ${calname}\", \"ICAL:calendar-color\": \"#73d216ff\", \"ICAL:calendar-order\": \"1\", \"tag\": \"VCALENDAR\"}" > ${DEST}/${ORGA}/${cal}/.Radicale.props

done

chown -R radicale.radicale ${DEST}/${ORGA}


# editable calendars

mkdir -m 0750 -p ${DEST}/${ORGA}-edit

for calname in Highlights Regular Other ; do
  cal=${calname,,}
  mkdir -m 0750 -p ${DEST}/${ORGA}-edit/${cal}

  echo "{\"C:calendar-description\": \"${ORGANAME}-${calname}\", \"C:supported-calendar-component-set\": \"VEVENT\", \"D:displayname\": \"${ORGANAME} ${calname} (edit)\", \"ICAL:calendar-color\": \"#73d216ff\", \"ICAL:calendar-order\": \"1\", \"tag\": \"VCALENDAR\"}" > ${DEST}/${ORGA}-edit/${cal}/.Radicale.props
done

chown -R radicale.radicale ${DEST}/${ORGA}-edit


# information output

echo "canonical orgname is \"${ORGA}\""
echo

echo "Configuration snippet for /etc/radicale/rights:"
echo

cat <<EOF
[${ORGA}-edit]
user = ^(user1|user2)$
collection = ^${ORGA}-edit(/.*)?$
permission = rw

[${ORGA}-public]
user = .*
collection = ^${ORGA}(/.*)?$
permission = r

EOF

