group_by(.album.sources.ytmusic.id)
| map(select(length >= 1) | {
    type: "album",
    sources: .[0].album.sources,
    name: .[0].album.name,
    year: .[0].album.year,
    thumbnail: .[0].thumbnail,
    artists: .[0].album.artists,
    songs: map({name, duration, sources, order})
  })
| map(select(.sources.ytmusic.id | startswith("RD") | not)) # No album
| .[]
