import { serve } from "https://deno.land/std@0.224.0/http/server.ts";

const resendApiKey = Deno.env.get("RESEND_API_KEY");
const ownerEmail = Deno.env.get("OWNER_NOTIFICATION_EMAIL");
const fromEmail = Deno.env.get("OWNER_NOTIFICATION_FROM") || "Asolo notifications <onboarding@resend.dev>";

serve(async (request) => {
  if (request.method !== "POST") {
    return new Response("Method not allowed", { status: 405 });
  }
  if (!resendApiKey || !ownerEmail) {
    return new Response("Notification secrets are not configured", { status: 500 });
  }

  const payload = await request.json();
  const record = payload.record || payload;
  const details = record.details || {};
  const enabled = details.enabled === true;
  const isActivity = record.event_type === "school_activity";
  const subject = isActivity
    ? `School activity detected: ${record.school_id}`
    : `${enabled ? "School access restored" : "School access blocked"}: ${record.school_id}`;
  const text = isActivity
    ? [
        `School ID: ${record.school_id}`,
        `Event: ${record.event_type}`,
        `Action: ${details.action || "unknown"}`,
        `Time: ${record.created_at || new Date().toISOString()}`,
      ].join("\n")
    : [
        `School ID: ${record.school_id}`,
        `Event: ${record.event_type}`,
        `Access: ${enabled ? "enabled" : "blocked"}`,
        `Message: ${details.message || "None"}`,
        `Time: ${record.created_at || new Date().toISOString()}`,
      ].join("\n");

  const response = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${resendApiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ from: fromEmail, to: [ownerEmail], subject, text }),
  });

  if (!response.ok) {
    return new Response(await response.text(), { status: 502 });
  }
  return new Response(JSON.stringify({ ok: true }), {
    headers: { "Content-Type": "application/json" },
  });
});
