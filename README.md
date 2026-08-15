[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# OpenEmailSequence

A Django app for **email drip sequences**. Write each email once, describe who should receive it as a queryset over your user model, and let a management command send it at the right moment. Sequences, campaigns, targeting rules, previews and unsubscribes are all managed from the Django admin — no code per campaign.

Built for Django 6 and Python 3.13. It powers the outreach follow-ups in [OpenOutreach](https://github.com/eracle/OpenOutreach), where it is vendored into the hub as a submodule.

## Concepts

| Object | What it is |
| --- | --- |
| `Sequence` | One email in a drip: subject, body, and the rules that decide who receives it. |
| `Campaign` | A group of sequences that belong together — a whole onboarding flow, for example. |
| `QuerySetRule` | One filter on the user queryset: a field path, a lookup type, and a value. |
| `SentEmail` | The record that a user already received a sequence, so nobody is mailed twice. |
| `UserUnsubscribe*` | Opt-outs at three levels: one sequence, one campaign, or everything. |

## Install

```bash
pip install git+https://github.com/eracle/OpenEmailSequence.git
```

Or vendor it as a submodule and put its root on `sys.path` — this is what the OpenOutreach hub does.

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "email_sequences",
]
```

```bash
python manage.py migrate email_sequences
```

Optional settings:

- `SEQUENCE_FROM_EMAIL` — From address for sent mail. A sequence's own `from_email` field wins; otherwise this, then `DEFAULT_FROM_EMAIL`.
- `SEQUENCE_UNSUBSCRIBE_USERS` — set to `True` to enable the unsubscribe views.
- `SEQUENCE_MESSAGE_CLASSES` — map a name to a custom message class, see *Custom messages*.

To expose the unsubscribe pages, include the URLs:

```python
# urls.py
path("unsubscribe/", include("email_sequences.urls")),
```

Email bodies can then contain `{{unsubscribe_link_sequence}}`, `{{unsubscribe_link_campaign}}` or `{{unsubscribe_link}}`, which render as signed, per-user links. The bundled templates are deliberately plain — override them in your own `templates/email_sequences/` directory.

## Targeting

A sequence picks its recipients through queryset rules over the user model: a field path (`last_login`, `date_joined`, `profile__credits`), a lookup type (`exact`, `gt`, `lt`, …) and a value. The admin autocompletes the available paths, including fields reachable through related models.

Date values accept natural-language offsets from now:

```
now-1 week
now+ 8days
now-4hours
```

Units: `seconds`/`s`, `minutes`/`m`, `hours`/`h`, `days`/`d`, `weeks`/`w`. Singular forms work with `1`.

Select a sequence in the admin and click **View timeline** to see exactly who would receive it, and when, before anything is sent.

## Sending

```bash
python manage.py send_sequences
```

The command sends every enabled sequence to the users its rules match, skipping anyone already in `SentEmail` and anyone unsubscribed. It is idempotent, so running it more often than strictly needed is safe.

Scheduling is deliberately left to the deployment — a cron entry, a systemd timer, whatever you already run:

```cron
0 9 * * 1-5  cd /app && python manage.py send_sequences
```

There is no in-process scheduler on purpose: a background thread inside the web process means one scheduler, and one send, per worker.

## Custom messages

Subclass `email_sequences.sequences.SequenceMessage` to change how a message is built — HTML, attachments, a different transport — and register it:

```python
SEQUENCE_MESSAGE_CLASSES = {
    "html": "myapp.messages.HtmlSequenceMessage",
}
```

The class can then be chosen per sequence in the admin.

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests run against `testsettings.py` on SQLite. `tests/testapp/` holds the throwaway models the suite needs.

## License

MIT — see [LICENSE](LICENSE).
