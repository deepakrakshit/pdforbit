import ErrorScreen from '@/components/ErrorScreen';

export default function ServerErrorPage() {
  return (
    <ErrorScreen
      statusCode={500}
      title="Houston, we have a problem."
      message="Something inside the PdfORBIT control system just misfired. Our engineers are probably already chasing it through space. Try refreshing or navigate back to safety."
    />
  );
}