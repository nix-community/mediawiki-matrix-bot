# mediawiki-matrix-bot


A Bot which publishes mediawiki Recent Changes from the [`/api.php` endpoint](https://nixos.wiki/api.php?action=help&modules=query%2Brecentchanges) to a matrix room.


## Development

```
$ nix-build
$ ./result/bin/mediawiki-matrix-bot config.json
```

## License
MIT
