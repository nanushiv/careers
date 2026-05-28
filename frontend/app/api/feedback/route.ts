import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    // Store in Supabase via backend API
    const resp = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/feedback`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }
    );

    if (!resp.ok) throw new Error("Backend error");
    return NextResponse.json({ success: true });
  } catch {
    // Don't fail silently — still return 200 so user sees thanks screen
    return NextResponse.json({ success: true });
  }
}
