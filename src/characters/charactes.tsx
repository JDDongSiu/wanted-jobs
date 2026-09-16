import type { JSX } from "react";
interface CharactersProps {
  className?: string;
}

const BASE_URL = "/wanted-jobs/";

// fix: reload시 해치만 느린이유?
const imageList = [
  {
    src: `${BASE_URL}images/ganadi-img.png`,
    alt: "가나디",
  },
  {
    src: `${BASE_URL}images/usagi-img.jpg`,
    alt: "우사기",
  },
  {
    src: `${BASE_URL}images/haechi-img.jpeg`,
    alt: "해치",
  },
] as const;

function Characters({
  className = "",
}: CharactersProps): JSX.Element {
  const containerClassName = ["mascots", className]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={containerClassName} aria-label="캐릭터 소개">
      {imageList.map((image, index) => (
        <img
          className={`mascot mascot-${index + 1}`}
          key={image.src}
          src={image.src}
          alt={image.alt}
          width={120}
          height={145}
          decoding="async"
        />
      ))}
    </div>
  );
}

export default Characters;
