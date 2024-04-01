# mediawiki-matrix-bot


A Bot which publishes mediawiki Recent Changes from the [`api.php` endpoint](https://wiki.nixos.org/w/api.php?action=help&modules=query%2Brecentchanges) to a matrix room.

## Configuration with `config.json`

### `baseurl`

The baseurl is the the domain and path of the mediawiki server, e.g.
`https://wiki.nixos.org`

### `api_path`
The default path to the api is `{baseurl}/api.php`. If the api endpoint is not
at the default location like in wiki.nixos.org it can be set to `/w/api.php` to
query a different endpoint.


## Development

```
$ nix-build
$ ./result/bin/mediawiki-matrix-bot config.json
```

## License
MIT
