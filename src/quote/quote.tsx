import { JSX, useEffect, useState } from "react";

// 캐릭터 하단 랜덤 속담 component
interface KoreanAdvice {
  author: string;
  message: string;
}

const ADVICE_API_URL =
  "https://korean-advice-open-api.vercel.app/api/advice";

async function fetchAdvice(
  signal: AbortSignal,
): Promise<KoreanAdvice> {
  const response = await fetch(ADVICE_API_URL, {
    signal,
  });

  return response.json() as Promise<KoreanAdvice>;
}

/**
 * error 발생 경우 특정 할 수 없어 finally 까지안감 log만 찍고 삭제.
 * 화면상에서 에러났을시 확인 불가. 아마 없을듯? 
 * 발생시 F12 개발자 모드 눌려서 확인
*/

// JS define function
function Quote(): JSX.Element {
  const [quotes, setQuotes] = useState<KoreanAdvice[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    const loadQuotes = async (): Promise<void> => {
      try {
        setIsLoading(true);

        const adviceList = await Promise.all([
          fetchAdvice(controller.signal),
        ]);

        setQuotes(adviceList);
      } catch (error) {
        setErrorMessage("명언을 불러오지 못했습니다.");
        console.log(error)
      } 
    };

    void loadQuotes();

  }, []);

  // NOTE: error 발생 경우 언제가 있을까..
  if (errorMessage) {
    return (
      <p className="hero-quote-status hero-quote-error">
        {errorMessage}
      </p>
    );
  }

  return (
    <>
      {quotes.map((quote, index) => (
        <blockquote
          className={"hero-quote"}
          key={`${quote.author}-${quote.message}`}
        >
          <span>{quote.message}</span>

          <span className="hero-quote-author">
            — {quote.author}
          </span>
        </blockquote>
      ))}
    </>
  );
}

export default Quote;
