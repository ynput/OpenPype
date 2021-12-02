Slack notification for publishing
---------------------------------

This module allows configuring profiles(when to trigger, for which combination of task, host and family)
and templates(could contain {} placeholder, as "{asset} published").

These need to be configured in 
```Project settings > Slack > Publish plugins > Notification to Slack```

Slack module must be enabled in System Setting, could be configured per Project.

## App installation

Slack app needs to be installed to company's workspace. Attached .yaml file could be
used, follow instruction https://api.slack.com/reference/manifests#using

## Settings

### Token
Most important for module to work is to fill authentication token 
```Project settings > Slack > Publish plugins > Token```

This token should be available after installation of app in Slack dashboard.
It is possible to create multiple tokens and configure different scopes for them.

### Profiles
Profiles are used to select when to trigger notification. One or multiple profiles
could be configured, 'family', 'task name' (regex available) and host combination is needed.

Eg. If I want to be notified when render is published from Maya, setting is:

- family: 'render'
- host: 'Maya'

### Channel
Message could be delivered to one or multiple channels, by default app allows Slack bot
to send messages to 'public' channels (eg. bot doesn't need to join channel first).

This could be configured in Slack dashboard and scopes might be modified.

### Message
Placeholders {} could be used in message content which will be filled during runtime.
Only keys available in 'anatomyData' are currently implemented.

Example of message content:
```{SUBSET} for {Asset} was published.```

Integration can upload 'thumbnail' file (if present in instance), for that bot must be 
manually added to target channel by Slack admin!
(In target channel write: ```/invite @OpenPypeNotifier``)