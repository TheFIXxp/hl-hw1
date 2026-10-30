package tech.soba4ka.hl.controller;

import java.net.URI;

import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;
import tech.soba4ka.hl.dto.ItemRequest;
import tech.soba4ka.hl.model.Item;
import tech.soba4ka.hl.repository.ItemRepository;

@RestController
@RequestMapping("/items")
@RequiredArgsConstructor
public class ItemController {
    private final ItemRepository repository;

    @PostMapping
    public ResponseEntity<Item> create(@RequestBody ItemRequest request) {
        request.validate();
        Item item = repository.create(request);
        return ResponseEntity.created(URI.create("/items/" + item.id())).body(item);
    }

    @GetMapping("/{id}")
    public Item get(@PathVariable long id) {
        return repository.find(id).orElseThrow(ItemController::notFound);
    }

    @PutMapping("/{id}")
    public Item update(@PathVariable long id, @RequestBody ItemRequest request) {
        request.validate();
        return repository.update(id, request).orElseThrow(ItemController::notFound);
    }

    private static ResponseStatusException notFound() {
        return new ResponseStatusException(HttpStatus.NOT_FOUND, "Item not found");
    }
}
