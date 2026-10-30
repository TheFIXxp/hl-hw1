package tech.soba4ka.hl.dto;

import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

public record ItemRequest(String name, String description) {
    public void validate() {
        if (name == null || name.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "name must not be blank");
        }
    }
}
