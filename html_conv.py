"""
Creates html-formatted text from telegram message with entitities.
For python3.8+.
Tested on Telethon 1.25.4.

It uses Telethon module just for type hinting. Feel free to delete it.

"""

from html import escape
from dataclasses import dataclass
from typing import List, Optional, Dict, NamedTuple, Callable, Union

from telethon.tl.types import TypeMessageEntity

class _Tag(NamedTuple):
    opening: str
    closing: str

@dataclass
class _PositionChange:
    to_open: List[_Tag]
    to_close: List[_Tag]
    br: bool

_TagMakerFunction = Callable[[TypeMessageEntity, str], _Tag]


class MessageToSyntax:

    def __init__(self, message: str, entities: Optional[List[TypeMessageEntity]]):
        
        # Usage of UTF-16 helps to get correct entity position.
        # Pros: There is no need of calculating codepoints and bytes. Just multiply offset/length by 2
        #       and everything will be correct.
        # Cons: Many utf encode/decode operaions.
        self._UTF_16 = 'utf-16-le'
        self._message = message
        self._entities = entities
        self.output = ''
        self._message_b16 = message.encode(self._UTF_16)
        self._positions: Dict[int, _PositionChange] = {}
    
    def to_syntax(self, type) -> str:
        """
        Performs the transformation of the message and entities into the target format.
        """
        if not self._entities and '\n' not in self._message:
            self.output = self._message
            return self.output

        # Load the dictionary of tags
        self._ENTITIES_TO_TAG = self.set_syntax_dict(type)

        # Retrieve the break tags from the dictionary or set them to defaults
        tag_paragraph = self._ENTITIES_TO_TAG.get('TagsParagraph', _Tag('', ''))
        tag_newline = self._ENTITIES_TO_TAG.get('TagsNewline', _Tag('', '\n'))

        # Ensure that start and end positions exist
        self._ensure_position_exists(0)
        self._ensure_position_exists(len(self._message_b16))
        
        # Prepare tag positions and line breaks
        self._prepare_entity_positions_utf16le(self._entities)
        self._prepare_br_positions()

        separations_points = list(sorted(self._positions.keys()))
        opened_tags: List[_Tag] = []

        # Main loop for generating tags
        for pos in range(len(separations_points)):
            index = separations_points[pos]
            next_index = separations_points[pos + 1] if index != len(self._message_b16) else None
            unchanged_part = self._message_b16[index:next_index].decode(self._UTF_16)

            # Close tags
            for t in self._positions[index].to_close:
                opened_tags.pop()
                self.output += t.closing

            # Handle line breaks
            if self._positions[index].br:
                if self._ENTITIES_TO_TAG['MessageEntityCode'] in opened_tags:
                    self.output += tag_newline.closing
                else:
                    self.output += tag_paragraph.closing + tag_paragraph.opening

            # Open tags
            for t in self._positions[index].to_open:
                opened_tags.append(t)
                self.output += t.opening

            # Append text without changes, removing \n
            self.output += escape(unchanged_part.replace('\n', ''))

        # Wrap the result in paragraph tags if necessary
        if tag_paragraph.opening or tag_paragraph.closing:
            self.output = tag_paragraph.opening + self.output + tag_paragraph.closing

        return self.output

    def _prepare_br_positions(self):
        # Process line breaks and ensure the corresponding positions in UTF-16 encoding
        for i in range(len(self._message)):
            if self._message[i] == '\n':
                i = len(self._message[0:i].encode(self._UTF_16))
                self._ensure_position_exists(i)
                self._positions[i].br = True

    def _prepare_entity_positions_utf16le(self, entities) -> None:
        # Prepare positions for each entity to set opening and closing tags
        if not entities:
            return

        for e in entities:
            start = e.offset * 2
            end = (e.offset + e.length) * 2
            self._ensure_position_exists(start)
            self._ensure_position_exists(end)
            tag = self._ENTITIES_TO_TAG[type(e).__name__]
            if tag:

                if callable(tag):
                    txt_bytes = self._message_b16[start:end]
                    txt = txt_bytes.decode(self._UTF_16)
                    tag = tag(e, txt)

                self._positions[start].to_open.append(tag)
                self._positions[end].to_close.insert(0, tag)

    def _ensure_position_exists(self, i: int):
        # Ensure that a position entry exists in _positions for the given index
        if i not in self._positions:
            self._positions[i] = _PositionChange([], [], False)

    def set_syntax_dict(self, type) -> Dict:
        # Set up the dictionary of entities to tags based on the syntax type specified
        match type.lower():
            case "docuwiki" | "dw":
                ENTITIES_TO_TAG: Dict[str, Union[None, _Tag, _TagMakerFunction]] = {
                    'MessageEntityBankCard': None,
                    'MessageEntityBlockquote': _Tag('> ', ''),
                    'MessageEntityBold': _Tag('**', '**'),
                    'MessageEntityBotCommand': None,
                    'MessageEntityCashtag': None,
                    'MessageEntityCode': _Tag("\n  ", ""),
                    'MessageEntityCustomEmoji': None,
                    'MessageEntityEmail': lambda e, s: _Tag(f'[[mailto:{escape(s)}|', ']]'),
                    'MessageEntityHashtag': None,
                    'MessageEntityItalic': _Tag('//', '//'),
                    'MessageEntityMention': lambda e, s: _Tag(f'[[https://t.me/{escape(s)}|', ']]'),
                    'MessageEntityMentionName': lambda e, s: _Tag(f'[[https://t.me/{escape(e.user_id)}|', ']]'),
                    'MessageEntityPhone':  lambda e, s: _Tag(f'[[tel:{escape(s)}|', ']]'),
                    'MessageEntityPre': lambda e, s: _Tag(f'<pre language="{escape(e.language)}">', '</pre>'),
                    'MessageEntitySpoiler': _Tag('??', '??'),
                    'MessageEntityStrike': _Tag('<del>', '</del>>'),
                    'MessageEntityTextUrl': lambda e, s: _Tag(f'[[{escape(e.url)}|', ']]'),
                    'MessageEntityUnderline': _Tag('__', '__'),
                    'MessageEntityUnknown': None,
                    'MessageEntityUrl': lambda e, s: _Tag(f'[[{escape(s)}|', ']]'),
                    'TagsParagraph': _Tag('', '\n'),
                    'TagsNewline': _Tag('', '\n'),
                }
            case "markdown" | "md":
                ENTITIES_TO_TAG: Dict[str, Union[None, _Tag, _TagMakerFunction]] = {
                    'MessageEntityBankCard': None,
                    'MessageEntityBlockquote': _Tag('> ', ''),
                    'MessageEntityBold': _Tag('**', '**'),
                    'MessageEntityBotCommand': None,
                    'MessageEntityCashtag': None,
                    'MessageEntityCode': _Tag('`', '`'),
                    'MessageEntityCustomEmoji': None,
                    'MessageEntityEmail': lambda e, s: _Tag('[', f'](mailto:{escape(s)})'),
                    'MessageEntityHashtag': None,
                    'MessageEntityItalic': _Tag('*', '*'),
                    'MessageEntityMention': lambda e, s: _Tag('[', f'](https://t.me/{escape(s)})'),
                    'MessageEntityMentionName': lambda e, s: _Tag('[', f'](https://t.me/{escape(e.user_id)})'),
                    'MessageEntityPhone': lambda e, s: _Tag('[', f'](tel:{escape(s)})'),
                    'MessageEntityPre': lambda e, s: _Tag(f'```{escape(e.language)}\n', '\n```'),
                    'MessageEntitySpoiler': _Tag('||', '||'),
                    'MessageEntityStrike': _Tag('~~', '~~'),
                    'MessageEntityTextUrl': lambda e, s: _Tag('[', f'](tel:{escape(e.url)})'),
                    'MessageEntityUnderline': _Tag('__', '__'),
                    'MessageEntityUnknown': None,
                    'MessageEntityUrl': lambda e, s: _Tag('[', f']({escape(s)})'),
                    'TagsParagraph': _Tag('', '\n'),
                    'TagsNewline': _Tag('', '\n'),
                }

            case "html":
                ENTITIES_TO_TAG: Dict[str, Union[None, _Tag, _TagMakerFunction]] = {
                    'MessageEntityBankCard': None,
                    'MessageEntityBlockquote': _Tag('<blockquote>', '</blockquote>'),
                    'MessageEntityBold': _Tag('<b>', '</b>'),
                    'MessageEntityBotCommand': None,
                    'MessageEntityCashtag': None,
                    'MessageEntityCode': _Tag('<pre>', '</pre>'),
                    'MessageEntityCustomEmoji': None,
                    'MessageEntityEmail': lambda e, s: _Tag(f'<a href="mailto:{escape(s)}">', '</a>'),
                    'MessageEntityHashtag': _Tag('<a href="#">', '</a>'),
                    'MessageEntityItalic': _Tag('<i>', '</i>'),
                    'MessageEntityMention': lambda e, s: _Tag(f'<a href="https://t.me/{escape(s)}">', '</a>'),
                    'MessageEntityMentionName': lambda e, s: _Tag(f'<a href="https://t.me/{escape(e.user_id)}">', '</a>'),
                    'MessageEntityPhone':  lambda e, s: _Tag(f'<a href="tel:{escape(s)}">', '</a>'),
                    'MessageEntityPre': lambda e, s: _Tag(f'<pre language="{escape(e.language)}">', '</pre>'),
                    'MessageEntitySpoiler': _Tag('[', ']'),
                    'MessageEntityStrike': _Tag('<s>', '</s>'),
                    'MessageEntityTextUrl': lambda e, s: _Tag(f'<a href="{escape(e.url)}">', '</a>'),
                    'MessageEntityUnderline': _Tag('<span style="text-decoration: underline">', '</span>'),
                    'MessageEntityUnknown': None,
                    'MessageEntityUrl': lambda e, s: _Tag(f'<a href="{escape(s)}">', '</a>'),
                    'TagsParagraph': _Tag('<p>', '</p>'),
                    'TagsNewline': _Tag('', '<br />'),
                }
            case _:
                ENTITIES_TO_TAG: Dict[str, Union[None, _Tag, _TagMakerFunction]] = {
                    'MessageEntityBankCard': None,
                    'MessageEntityBlockquote': _Tag(f'«', '»'),
                    'MessageEntityBold': None,
                    'MessageEntityBotCommand': None,
                    'MessageEntityCashtag': None,
                    'MessageEntityCode': None,
                    'MessageEntityCustomEmoji': None,
                    'MessageEntityEmail': None,
                    'MessageEntityHashtag': None,
                    'MessageEntityItalic': None,
                    'MessageEntityMention': None,
                    'MessageEntityMentionName':  lambda e, s: _Tag('', f' ({escape(e.user_id)})'),
                    'MessageEntityPhone': None,
                    'MessageEntityPre': None,
                    'MessageEntitySpoiler': None,
                    'MessageEntityStrike': None,
                    'MessageEntityTextUrl':  lambda e, s: _Tag('', f' ({escape(e.url)})'),
                    'MessageEntityUnderline': None,
                    'MessageEntityUnknown': None,
                    'MessageEntityUrl': None,
                    'TagsParagraph': _Tag('', '\n'),
                    'TagsNewline': _Tag('', '\n'),
                }
                # text by default
        return ENTITIES_TO_TAG


    
