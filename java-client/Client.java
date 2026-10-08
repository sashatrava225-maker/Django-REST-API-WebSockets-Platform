import org.java_websocket.client.WebSocketClient;
import org.java_websocket.handshake.ServerHandshake;

import java.net.URI;

public class Client extends WebSocketClient {

    public Client(URI serverUri) {
        super(serverUri);
    }

    @Override
    public void onOpen(ServerHandshake handshakedata) {
        System.out.println("CONNECTED");

        // тестовий запит (як у твоєму FastAPI)
        send("{\"action\":\"add\",\"name\":\"apple from java\",\"quantity\":1}");
    }

    @Override
    public void onMessage(String message) {
        System.out.println("RECEIVED: " + message);
    }

    @Override
    public void onClose(int code, String reason, boolean remote) {
        System.out.println("CLOSED: " + reason);
    }

    @Override
    public void onError(Exception ex) {
        System.out.println("ERROR:");
        ex.printStackTrace();
    }

    public static void main(String[] args) throws Exception {
        Client client = new Client(new URI("ws://localhost:8000/ws"));
        client.connect();
    }
}
