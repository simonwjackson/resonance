[inputs]
| map(
  if type != "array" then [.] else . end
  | map(
      .artists[] as $artist
      | {
          type: "artist",
          name: $artist.name,
          sources: $artist.sources,
          albums: [{
              name: .name,
              year: .year,
              thumbnail: .thumbnail,
              sources: .sources,
              songs: .songs
                | map({
                    name,
                    duration,
                    sources
                })
          }]
      }
  )
  | .[]
)
| group_by(.sources.ytmusic.id)
| map({
    artist: .[0].name,
    sources: .[0].sources,
    albums: [.[].albums[]]
  })
| .[]
