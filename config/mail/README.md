# Mail client configuration

This directory contains the reusable, pull-only configuration for `aerc`,
`isync`/`mbsync`, `notmuch`, `msmtp`, and `oama`.
The installer assumes those programs are already installed; this repository
does not currently manage Linux packages.

Run the installer after cloning the dotfiles:

```bash
automation/mail/install-mail.sh
```

The installer links shared UI settings, query maps, notmuch hooks, helper
scripts, and sanitized examples. It deliberately preserves these local files:

- `~/.config/aerc/accounts.conf`
- `~/.config/isync/mbsyncrc`
- `~/.config/notmuch/personal/config`
- `~/.config/notmuch/work/config`
- `~/.config/msmtp/config`
- `~/.config/oama/config.yaml`

Create those files from their `.example` counterparts and keep them mode
`0600`. They contain account identities, OAuth client configuration, or the
commands that select credentials from the local keyring. Never copy OAuth
tokens, refresh tokens, client secrets, passwords, or mail data into this
repository.

Replace every `USER`, `Your Name`, and `example.com` placeholder when creating
the local files. The aerc examples point directly at each notmuch database;
notmuch profile names are not valid aerc source paths.

The isync configuration intentionally remains at
`~/.config/isync/mbsyncrc`. Use `mbsync -c ~/.config/isync/mbsyncrc` when
running it directly; the tracked sync helpers already pass that option.

Mail synchronization remains pull-only: `mbsync` uses `Sync Pull`, does not
remove or expunge remote mail, and aerc routes outgoing messages to
`mail-send-disabled`. The tracked msmtp file is only an inactive example.
