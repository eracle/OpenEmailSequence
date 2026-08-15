Extending Django Sequence
=====================

Django Sequence provides a way for you to extend all the functionality through abstract classes.

These classes provide all the functions required to make a sequence work, but they don't provide any data column.
Beware though, these classes use the attributes from the concrete sequence classes shown in the rest of the docs.

For you to extend them you need to overwite the implementations on your own.
Since this classes handle themselves mainly through related models, as long as you maintain the inteface you can extend in any way you want.

`AbstractSequence`

This provides the data model for the sequence, here you can customize the data model of the message itself.
It has a `sequence` property with the actual logic of sending the message.


`AbstractSentEmail`

This provides the data model for the log of sent sequences.
This will help you if you want to customize what's being saved on the database after a message is sent.
Defines a relationship with the User model of your app, that you can access through `user.sent_emails`.
Defines a relationship with the Sequence model. You can access that relationship through `sequence.sent_emails`.


`AbstractQuerySetRule`

This provides the query rules applied for sending the sequences.
Defines a relationship with the Sequence model. You can access that relationship through `sequence.queryset_rules`.
