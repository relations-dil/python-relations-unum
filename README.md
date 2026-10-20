# python-relations-unum

Source for locally using multiple Unifist sources as a single Unum

Part of [Relations](https://github.com/relations-dil/python-relations). Source agnostic: it builds on the
core library's `Source`, `Model` and hooks only, so it works over any relations source.

**Status:** scaffold. See the first ticket for the design and what done looks like.

## Models under `/model`

`relations_unum.RestSource` is a [relations-rest](https://github.com/relations-dil/python-relations-rest) source for an API that serves its models under `/model`, as [relations-unifist](https://github.com/relations-dil/python-relations-unifist) does: `/model/{singular}` and `/model/{singular}/<id>`. It takes what `relations_rest.Source` does and adds `/model` to the url, so an app opts in by making its source from it, giving the API's url without `/model`:

```python
relations_unum.RestSource("cumulus", "https://cumulus.example.com")
```

A model's `ENDPOINT` is relative to `/model`. `relations_rest.Source` still reads models at the root of its url, for APIs that serve them there.
