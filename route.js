import { NextResponse } from "next/server";

export async function GET() {
  const url = new URL("https://id.ctrader.com/my/settings/openapi/grantingaccess/");
  url.searchParams.set("client_id", process.env.CTRADER_CLIENT_ID);
  url.searchParams.set("redirect_uri", process.env.CTRADER_REDIRECT_URI);
  url.searchParams.set("scope", "trading");
  url.searchParams.set("product", "web");
  return NextResponse.redirect(url.toString());
}
