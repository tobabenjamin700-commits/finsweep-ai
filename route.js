import { NextResponse } from "next/server";

export async function GET(req) {
  const code = new URL(req.url).searchParams.get("code");
  if (!code) return NextResponse.json({ error: "Missing code" }, { status: 400 });

  const t = new URL("https://openapi.ctrader.com/apps/token");
  t.searchParams.set("grant_type", "authorization_code");
  t.searchParams.set("code", code);
  t.searchParams.set("redirect_uri", process.env.CTRADER_REDIRECT_URI);
  t.searchParams.set("client_id", process.env.CTRADER_CLIENT_ID);
  t.searchParams.set("client_secret", process.env.CTRADER_CLIENT_SECRET);

  const tok = await (await fetch(t)).json();
  if (!tok.accessToken) return NextResponse.json(tok, { status: 400 });

  await fetch(`${process.env.ENGINE_URL}/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-engine-secret": process.env.ENGINE_SECRET },
    body: JSON.stringify({ accessToken: tok.accessToken }),
  });
  return NextResponse.redirect(new URL("/", req.url));
}
