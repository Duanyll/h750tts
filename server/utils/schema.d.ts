declare namespace SubBoard {
    interface EchoRequest {
        command: "echo";
        message: string;
    }

    interface LedRequest {
        command: "led";
        on: boolean;
    }

    interface PlayRequest {
        command: "play";
        list: number[];
        priority: number;
    }

    interface SpeakRequest {
        command: "speak";
        text: string;
        priority: number;
    }

    interface StopRequest {
        command: "stop";
    }

    interface VolumeRequest {
        command: "volume";
        volume: number;
    }

    interface QueryRequest {
        command: "query";
    }

    type Request = EchoRequest
        | LedRequest
        | PlayRequest
        | SpeakRequest
        | StopRequest
        | VolumeRequest;

    interface QueryResponseData {
        volume: number;
        isPlaying: boolean;

        isMoving: boolean;
        facing: number;
        distance: number;
    }

    interface SuccessResponse<TData = void> {
        code: 0;
        message: string;
        data: TData;
    }

    interface ErrorResponse {
        code: number;
        message: string;
    }

    type Response<TData = void> = SuccessResponse<TData> | ErrorResponse;
}

declare namespace Server {
    // Request: OpenMV -> Server
    // Response: Server -> OpenMV
    interface SubBoardResponse {
        type: "subboard";
        command: SubBoard.Request;
    }

    interface DirectionResponse {
        type: "direction";
        direction: "front" | "left" | "right" | "stop" | "far_left" | "far_right";
    }

    interface TextResponse {
        type: "text";
        text: string;
        priority: number;
    }

    type Response = SubBoardResponse | DirectionResponse | TextResponse;
}