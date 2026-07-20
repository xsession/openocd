export interface DapRequest {
  seq: number;
  type: 'request';
  command: string;
  arguments?: any;
}

export interface DapResponse {
  seq: number;
  type: 'response';
  request_seq: number;
  success: boolean;
  command: string;
  message?: string;
  body?: any;
}

export interface DapEvent {
  seq: number;
  type: 'event';
  event: string;
  body?: any;
}

export class DapTransport {
  private input = Buffer.alloc(0);
  private sequence = 1;
  private readonly listeners: Array<(request: DapRequest) => void> = [];

  public constructor() {
    process.stdin.on('data', (chunk: Buffer) => this.handleData(chunk));
    process.stdin.on('error', (error: Error) => {
      this.event('output', { category: 'stderr', output: `${error.stack ?? error.message}\n` });
    });
  }

  public onRequest(listener: (request: DapRequest) => void): void {
    this.listeners.push(listener);
  }

  public response(request: DapRequest, body?: any): void {
    this.send({
      seq: this.sequence++,
      type: 'response',
      request_seq: request.seq,
      success: true,
      command: request.command,
      body,
    });
  }

  public error(request: DapRequest, error: unknown): void {
    const message = error instanceof Error ? error.message : String(error);
    this.send({
      seq: this.sequence++,
      type: 'response',
      request_seq: request.seq,
      success: false,
      command: request.command,
      message,
      body: { error: { id: 1, format: message, showUser: true } },
    });
  }

  public event(event: string, body?: any): void {
    this.send({ seq: this.sequence++, type: 'event', event, body });
  }

  private handleData(chunk: Buffer): void {
    this.input = Buffer.concat([this.input, chunk]);
    while (true) {
      const headerEnd = this.input.indexOf('\r\n\r\n');
      if (headerEnd < 0) {
        return;
      }
      const header = this.input.subarray(0, headerEnd).toString('ascii');
      const match = header.match(/Content-Length:\s*(\d+)/i);
      if (!match) {
        this.input = this.input.subarray(headerEnd + 4);
        continue;
      }
      const length = Number(match[1]);
      const messageStart = headerEnd + 4;
      if (this.input.length < messageStart + length) {
        return;
      }
      const body = this.input.subarray(messageStart, messageStart + length).toString('utf8');
      this.input = this.input.subarray(messageStart + length);
      try {
        const request = JSON.parse(body) as DapRequest;
        for (const listener of this.listeners) {
          listener(request);
        }
      } catch (error) {
        this.event('output', { category: 'stderr', output: `Invalid DAP request: ${String(error)}\n` });
      }
    }
  }

  private send(message: DapResponse | DapEvent): void {
    const body = Buffer.from(JSON.stringify(message), 'utf8');
    process.stdout.write(`Content-Length: ${body.length}\r\n\r\n`);
    process.stdout.write(body);
  }
}
