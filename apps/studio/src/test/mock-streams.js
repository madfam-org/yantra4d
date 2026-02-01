/**
 * Create a ReadableStream from an array of SSE lines.
 * Each line should be a complete SSE data line, e.g. 'data: {"event":"complete",...}'
 *
 * @param {string[]} lines - SSE lines to include in the stream
 * @returns {ReadableStream}
 */
export function createSSEStream(lines) {
  const text = lines.join('\n')
  const encoder = new TextEncoder()
  return new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(text))
      controller.close()
    }
  })
}
