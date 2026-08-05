Instructions
Day 1 Homework: Build a Lakebase-Powered AI Support App
Objective
Build and deploy a small Databricks App backed by Lakebase. Your app will become the foundation for the context-engineering and AI-agent projects later in the boot camp.

Scenario
You are building an internal support system where users can create support tickets and add messages to those tickets.

Your application must store its operational data in Lakebase.

Requirements
1. Create the Lakebase schema
Create at least these two related tables:

tickets

ticket_id

title

status

created_by

created_at

ticket_messages

message_id

ticket_id

message_text

author

created_at

The ticket_messages.ticket_id column must reference a ticket in the tickets table.

You may add additional columns or tables.

2. Add sample data
Your database must contain:

At least three support tickets

At least two messages for each ticket

At least two different ticket statuses, such as open, in_progress, or resolved

3. Build a Databricks App
Create an app that allows a user to:

View all support tickets

Select a ticket and view its messages

Create a new ticket

Add a message to an existing ticket

Update a ticket’s status

The app must read from and write to Lakebase. Hard-coded application data does not count.

4. Deploy and test the app
Deploy the app using Databricks Apps and confirm that:

Existing tickets load from Lakebase

A new ticket can be created

A message can be added

A ticket’s status can be updated

Changes remain after refreshing the app

What to Submit
Submit one document or form response containing:

Your Databricks App URL

Your source code zipped up

A screenshot of the deployed application

A screenshot showing the Lakebase tables and sample records

A short reflection of 3–5 sentences answering:

What was the most difficult part?

How is Lakebase different from storing this data in a traditional analytics table?

What feature would you add next?

Bonus Challenges
Earn recognition for completing one or more of these:

Add ticket priority or category

Add filtering by ticket status

Add input validation and helpful error messages

Display ticket statistics

Add delete functionality with a confirmation step

Improve the visual design of the application

Important
Do not submit passwords, database credentials, API keys, or secret values. Your application should access credentials through the Databricks environment or another secure configuration method.
