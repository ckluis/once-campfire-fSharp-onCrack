// Port of rust/crates/views/src/searches.rs (the view-model; the template is Templates/Searches)
/// Views for `reference/app/views/searches`, plus `SearchesHelper`.
module Campfire.Views.Searches

open Campfire.Routes
open Campfire.Views.Helpers
open Campfire.Views.Messages

/// What `searches/index` shows.
type IndexView =
    { /// `@query`: `params[:q]` with non-word characters turned into spaces, when present.
      Query: string option
      /// `params[:q]` as submitted, the search field's value.
      Q: string option
      /// `Message.search_reachable(Current.user, query)`: the newest 100 matches by message id, oldest first.
      Messages: MessageItem list
      /// `Current.user.searches.ordered.pluck(:query)`.
      RecentSearches: string list
      /// `last_room_visited.id`, where the exit button goes.
      ReturnToRoomId: int64 }

/// `searches_path(q: query)`.
let searchPath (query: string) : string = $"{Routes.searches ()}?q={Url.cgiEscape query}"
