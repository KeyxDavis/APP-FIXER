# Owner controls

This feature gives the application owner a separate portal for managing all cloud schools. It intentionally never reads, stores, or emails school passwords. Passwords remain in Supabase Auth; use Supabase's password reset flow when an account needs recovery.

## One-time Supabase setup

1. Run `database_schema.sql` in the Supabase SQL Editor.
2. Run `owner_control.sql`.
3. Create your owner account in Supabase Authentication with the email address that should receive notifications.
4. Copy that account's UUID from Authentication and register it as an owner:

```sql
insert into public.platform_owners (user_id, email)
values ('YOUR-AUTH-USER-UUID', 'your-gmail@example.com');
```

5. Open `owner_portal.html` in a browser, enter the project URL and anon key, and sign in with that owner account.

Only accounts present in `platform_owners` can list schools or block access. Keep the Supabase service-role key out of the portal and out of the Kivy app.

## Gmail notifications

The notification function uses Resend to deliver messages to your Gmail inbox. The recipient can be Gmail; Resend is the server-side sender.

1. Create a Resend account and verify a sending domain, or use the test sender while developing.
2. Deploy `supabase/functions/owner-notify/index.ts` as the `owner-notify` Supabase Edge Function.
3. Add these Edge Function secrets in Supabase:

```text
RESEND_API_KEY=re_...
OWNER_NOTIFICATION_EMAIL=your-gmail@example.com
OWNER_NOTIFICATION_FROM=Asolo notifications <alerts@your-verified-domain.example>
```

4. Create a Supabase Database Webhook for `public.owner_events` inserts and point it to the `owner-notify` function URL.

The email is sent when school access changes and on the first recorded activity from each school per day. The portal also shows each school's member count and latest activity timestamp.

## Blocking a school

Use the portal's **Block access** button. The school app will display the configured message and close during its next status check. Access can be restored with **Restore access**.
