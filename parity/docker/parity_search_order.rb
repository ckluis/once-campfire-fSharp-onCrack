# Parity-only (baked into the campfire-reference image by parity/docker/Dockerfile, not part of
# reference/): the reference lists search results in the order current upstream Rails does.
#
# reference/ is Rails 90b3300, whose SearchesController lists the last 100 matches by created_at
# (`reachable_messages.search(query).last(100)`, `search` ending in `.ordered`). Since Rails dbc7620
# (`Message.search_reachable`, built on edaab3e's rowid order) upstream lists the newest 100 matches
# by message id, which is the full-text index's rowid, shown oldest first, and upstream's benchmark
# contract checks that order. onCrack follows current upstream, so the oracle has to as well. This
# is the whole of the change: the same scope, the same 100, reordered by the index's rowid.
#
# It matters when ids and times disagree. The default seed's fixtures do (the search for "launch" lists
# nine messages in a different order by time than by id), so `search/submitted` renders differently.
#
# PARITY_SEARCH_ORDER=created_at restores 90b3300's order, for running the F# port (which keeps it)
# against this oracle.
unless ENV["PARITY_SEARCH_ORDER"] == "created_at"
  Rails.application.config.to_prepare do
    SearchesController.class_eval do
      private
        def set_messages
          if query.present?
            @messages = Current.user.reachable_messages.search(query).reorder("idx.rowid").last(100)
          else
            @messages = Message.none
          end
        end
    end
  end
end
