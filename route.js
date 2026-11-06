export const dynamic = "force-dynamic";

export async function GET(_req, { params }) {
  const { path } = await params;
  try {
    const r = await fetch(`${process.env.ENGINE_URL}/${path.join("/")}`, { cache: "no-store" });
    return Response.json(await r.json());
  } catch {
    return Response.json({ connected: false, error: "Engine unreachable (may be waking up)" }, { status: 200 });
  }
}
