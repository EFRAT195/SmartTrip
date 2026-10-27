
type WikiPage = {
  title: string;
  thumbnail?: {
    source: string;
  };
};

type WikiResponse = {
  query?: {
    pages?: Record<string, WikiPage>;
  };
};

export async function getAttractionImage(
  attractionName: string
): Promise<string | null> {
  const params = new URLSearchParams({
    action: "query",
    generator: "search",
    gsrsearch: `"${attractionName}"`,
    gsrlimit: "5",
    prop: "pageimages",
    piprop: "thumbnail",
    pithumbsize: "700",
    format: "json",
    origin: "*",
  });

  try {
    const response = await fetch(
      `https://he.wikipedia.org/w/api.php?${params}`
    );

    if (!response.ok) {
      return null;
    }

    const data: WikiResponse = await response.json();
    const pages = Object.values(data.query?.pages ?? {});

    const matchingPage = pages.find(
      (page) =>
        page.title.includes(attractionName) &&
        page.thumbnail?.source
    );

    return matchingPage?.thumbnail?.source ?? null;
  } catch {
    return null;
  }
}
