#!/bin/bash

# This is a hook invoked by radicale to
#   - sanitize the changed entries according to ${SANITIZER}
#   - do a fancy linking strategy to push edited entries to readonly calendars
#   - commit the changes into a git.

USER=${1-Anonymous}

BASEPATH=${PWD}
SANITIZER=/var/lib/radicale/sanical.py

ORGLIST="hasi c3si jkf"

for ORG in ${ORGLIST} ; do
  ORGEDITPATH=${BASEPATH}/collection-root/${ORG}-edit/

  git add -A -N ${ORGEDITPATH}
  for f in `git diff --name-only ${ORGEDITPATH}` ; do
    case ${f} in
      *-edit/highlights/*ics)
           ${SANITIZER} -c HIGHLIGHT -i "$f"
           ;;
      *-edit/regular/*ics)
           ${SANITIZER} -c EVENT -i "$f"
           ;;
      *-edit/other/*ics)
           ${SANITIZER} -c OTHER -i "$f"
           ;;
    esac
  done
done


for ORG in ${ORGLIST} ; do
  ORGPATH=${BASEPATH}/collection-root/${ORG}/

  cd ${ORGPATH}/all
  ln -f -s ../../${ORG}-edit/other/*ics .
  ln -f -s ../../${ORG}-edit/regular/*ics .
  ln -f -s ../../${ORG}-edit/highlights/*ics .
  find . -xtype l -delete

  cd ${ORGPATH}/events
  ln -f -s ../../${ORG}-edit/regular/*ics .
  ln -f -s ../../${ORG}-edit/highlights/*ics .
  find . -xtype l -delete

  cd ${ORGPATH}/highlights
  ln -f -s ../../${ORG}-edit/highlights/*ics .
  find . -xtype l -delete

  cd ${BASEPATH}
done

git add -A && (git diff --cached --quiet || git commit -m "Changes by ${USER}")
