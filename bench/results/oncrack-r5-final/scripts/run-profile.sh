#!/usr/bin/env bash
# run-profile.sh NAME: the exact harness arguments of a normal-N or mixed-N session (as round 4: five routes normal, four mixed).
name=$1
apps=rails,rust,c,fsharp,oncrack,oncrack-cached
case $name in
  normal-*) args="--apps $apps --routes room_show,messages_page,sidebar,search,post_message" ;;
  mixed-*)  args="--apps $apps --mixed-write-rate 10 --routes room_show,messages_page,sidebar,search" ;;
esac
exec "$(dirname "$0")/session.sh" "$name" $args
