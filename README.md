# TelethonMessageConverter
Telegram/Telethon message with entities to HTML converter.
It needs `message` and `entities` fields from `telethon.tl.custom.message.Message` objects. Use it like this:

```python
from TelethonMessageConverter import MessageToSyntax
    
for msg in tg_client.iter_messages(invite_link):
    converter = MessageToSyntax(msg.message, msg.entities)
    html = converter.to_syntax('html')
 ``` 
 
 Not all `MessageEntity*` items are processing. You may add new one to `_ENTITIES_TO_TAG` dict.

### See also

  - [Telegram docs. Styled text with message entities.](https://core.telegram.org/api/entities)
